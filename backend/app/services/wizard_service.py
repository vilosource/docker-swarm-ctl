"""
Wizard Service

Handles the business logic for the wizard framework, including
state management, step validation, and progress tracking.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import WizardInstance, WizardStatus, WizardType, User
from app.core.exceptions import ValidationError, AuthorizationError, NotFoundError
from app.core.logging import logger
from app.services.wizards.ssh_host_wizard import get_ssh_host_wizard


class WizardService:
    """Service for managing wizard instances"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_wizard(
        self,
        user: User,
        wizard_type: WizardType,
        resource_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> WizardInstance:
        """
        Create a new wizard instance
        
        Args:
            user: User starting the wizard
            wizard_type: Type of wizard to create
            resource_id: ID of resource being configured
            resource_type: Type of resource
            initial_state: Initial state data
            
        Returns:
            Created wizard instance
        """
        # Check for existing in-progress wizard for the same resource
        if resource_id:
            existing = await self.db.execute(
                select(WizardInstance).where(
                    and_(
                        WizardInstance.user_id == user.id,
                        WizardInstance.resource_id == resource_id,
                        WizardInstance.status == WizardStatus.in_progress
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValidationError("An in-progress wizard already exists for this resource")
        
        # Get wizard configuration
        wizard_config = self._get_wizard_config(wizard_type)
        
        # Create wizard instance
        wizard = WizardInstance(
            user_id=user.id,
            wizard_type=wizard_type,
            version=wizard_config["version"],
            resource_id=resource_id,
            resource_type=resource_type,
            total_steps=wizard_config["total_steps"],
            state=initial_state or {},
            wizard_metadata={"step_history": []}
        )
        
        self.db.add(wizard)
        await self.db.commit()
        await self.db.refresh(wizard)
        
        logger.info(f"Created wizard {wizard.id} of type {wizard_type} for user {user.username}")
        
        return wizard
    
    async def get_wizard(
        self,
        wizard_id: UUID,
        user: User
    ) -> WizardInstance:
        """
        Get a wizard instance by ID
        
        Args:
            wizard_id: Wizard ID
            user: User requesting the wizard
            
        Returns:
            Wizard instance
            
        Raises:
            NotFoundError: If wizard not found
            AuthorizationError: If user doesn't own the wizard
        """
        result = await self.db.execute(
            select(WizardInstance).where(WizardInstance.id == wizard_id)
        )
        wizard = result.scalar_one_or_none()
        
        if not wizard:
            raise NotFoundError("wizard", str(wizard_id))
        
        if wizard.user_id != user.id and user.role != "admin":
            raise AuthorizationError("You don't have access to this wizard")
        
        return wizard
    
    async def update_step(
        self,
        wizard_id: UUID,
        user: User,
        step_data: Dict[str, Any]
    ) -> WizardInstance:
        """
        Update the current step's data
        
        Args:
            wizard_id: Wizard ID
            user: User updating the wizard
            step_data: Data for the current step
            
        Returns:
            Updated wizard instance
        """
        logger.info(f"update_step called - wizard_id: {wizard_id}, step_data: {step_data}")
        
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot update wizard in {wizard.status} status")
        
        logger.info(f"Current wizard state before update: {wizard.state}")
        logger.info(f"Current step: {wizard.current_step}")
        
        # Validate step data based on wizard type and current step
        self._validate_step_data(wizard, step_data)
        
        # Update state (JSONB needs assignment, not update)
        new_state = dict(wizard.state)
        new_state.update(step_data)
        wizard.state = new_state
        wizard.updated_at = datetime.utcnow()
        
        logger.info(f"New state to be saved: {new_state}")
        
        # Track step update in metadata (JSONB needs assignment)
        new_metadata = dict(wizard.wizard_metadata)
        if "step_history" not in new_metadata:
            new_metadata["step_history"] = []
        new_metadata["step_history"].append({
            "step": wizard.current_step,
            "action": "update",
            "timestamp": datetime.utcnow().isoformat()
        })
        wizard.wizard_metadata = new_metadata
        
        await self.db.commit()
        await self.db.refresh(wizard)
        
        logger.info(f"State after commit and refresh: {wizard.state}")
        
        return wizard
    
    async def next_step(
        self,
        wizard_id: UUID,
        user: User
    ) -> WizardInstance:
        """
        Move to the next step
        
        Args:
            wizard_id: Wizard ID
            user: User advancing the wizard
            
        Returns:
            Updated wizard instance
        """
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot advance wizard in {wizard.status} status")
        
        if wizard.current_step >= wizard.total_steps - 1:
            raise ValidationError("Already at the last step")
        
        # Validate current step is complete
        if not self._is_step_complete(wizard):
            raise ValidationError("Current step is not complete")
        
        # Advance to next step
        wizard.current_step += 1
        wizard.updated_at = datetime.utcnow()
        
        # Track navigation
        new_metadata = dict(wizard.wizard_metadata)
        new_metadata["step_history"].append({
            "step": wizard.current_step,
            "action": "next",
            "timestamp": datetime.utcnow().isoformat()
        })
        wizard.wizard_metadata = new_metadata
        
        await self.db.commit()
        await self.db.refresh(wizard)
        
        return wizard
    
    async def previous_step(
        self,
        wizard_id: UUID,
        user: User
    ) -> WizardInstance:
        """
        Go back to the previous step
        
        Args:
            wizard_id: Wizard ID
            user: User navigating the wizard
            
        Returns:
            Updated wizard instance
        """
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot navigate wizard in {wizard.status} status")
        
        if wizard.current_step <= 0:
            raise ValidationError("Already at the first step")
        
        # Go back to previous step
        wizard.current_step -= 1
        wizard.updated_at = datetime.utcnow()
        
        # Track navigation
        new_metadata = dict(wizard.wizard_metadata)
        new_metadata["step_history"].append({
            "step": wizard.current_step,
            "action": "back",
            "timestamp": datetime.utcnow().isoformat()
        })
        wizard.wizard_metadata = new_metadata
        
        await self.db.commit()
        await self.db.refresh(wizard)
        
        return wizard
    
    async def test_step(
        self,
        wizard_id: UUID,
        user: User,
        test_type: str
    ) -> Dict[str, Any]:
        """
        Run validation/test for the current step
        
        Args:
            wizard_id: Wizard ID
            user: User running the test
            test_type: Type of test to run
            
        Returns:
            Test results
        """
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot test wizard in {wizard.status} status")
        
        # Run test based on wizard type and current step
        test_result = await self._run_step_test(wizard, test_type)
        
        # Store test result in metadata
        new_metadata = dict(wizard.wizard_metadata)
        if "test_results" not in new_metadata:
            new_metadata["test_results"] = {}
        new_metadata["test_results"][f"step_{wizard.current_step}_{test_type}"] = {
            "result": test_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        wizard.wizard_metadata = new_metadata
        
        await self.db.commit()
        
        return test_result
    
    async def complete_wizard(
        self,
        wizard_id: UUID,
        user: User
    ) -> Dict[str, Any]:
        """
        Complete the wizard and perform final actions
        
        Args:
            wizard_id: Wizard ID
            user: User completing the wizard
            
        Returns:
            Completion result with created resources
        """
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot complete wizard in {wizard.status} status")
        
        if wizard.current_step < wizard.total_steps - 1:
            raise ValidationError("Not all steps completed")
        
        if not self._is_step_complete(wizard):
            raise ValidationError("Current step is not complete")
        
        # Perform wizard-specific completion actions
        try:
            result = await self._complete_wizard_actions(wizard)
            
            # Mark wizard as completed
            wizard.status = WizardStatus.completed
            wizard.completed_at = datetime.utcnow()
            wizard.resource_id = result.get("resource_id")
            wizard.resource_type = result.get("resource_type")
            
            new_metadata = dict(wizard.wizard_metadata)
            new_metadata["completion_result"] = result
            wizard.wizard_metadata = new_metadata
            
            await self.db.commit()
            
            logger.info(f"Completed wizard {wizard.id} for user {user.username}")
            
            return result
        except Exception as e:
            logger.error(f"Error completing wizard {wizard.id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def cancel_wizard(
        self,
        wizard_id: UUID,
        user: User
    ) -> None:
        """
        Cancel a wizard
        
        Args:
            wizard_id: Wizard ID
            user: User cancelling the wizard
        """
        wizard = await self.get_wizard(wizard_id, user)
        
        if wizard.status != WizardStatus.in_progress:
            raise ValidationError(f"Cannot cancel wizard in {wizard.status} status")
        
        # Perform cleanup if needed
        await self._cleanup_wizard(wizard)
        
        # Mark as cancelled
        wizard.status = WizardStatus.cancelled
        wizard.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Cancelled wizard {wizard.id} for user {user.username}")
    
    async def list_user_wizards(
        self,
        user: User,
        status: Optional[WizardStatus] = None,
        wizard_type: Optional[WizardType] = None
    ) -> List[WizardInstance]:
        """
        List wizards for a user
        
        Args:
            user: User whose wizards to list
            status: Filter by status
            wizard_type: Filter by type
            
        Returns:
            List of wizard instances
        """
        query = select(WizardInstance).where(WizardInstance.user_id == user.id)
        
        if status:
            query = query.where(WizardInstance.status == status)
        
        if wizard_type:
            query = query.where(WizardInstance.wizard_type == wizard_type)
        
        query = query.order_by(WizardInstance.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def _get_wizard_config(self, wizard_type: WizardType) -> Dict[str, Any]:
        """Get configuration for a wizard type"""
        configs = {
            WizardType.ssh_host_setup: {
                "version": 1,
                "total_steps": 5,
                "steps": [
                    "connection_details",
                    "authentication",
                    "ssh_test",
                    "docker_test",
                    "confirmation"
                ]
            },
            WizardType.swarm_init: {
                "version": 1,
                "total_steps": 4,
                "steps": [
                    "cluster_config",
                    "network_config",
                    "security_config",
                    "confirmation"
                ]
            }
        }
        
        return configs.get(wizard_type, {"version": 1, "total_steps": 1})
    
    def _validate_step_data(self, wizard: WizardInstance, step_data: Dict[str, Any]) -> None:
        """Validate data for a specific step"""
        if wizard.wizard_type == WizardType.ssh_host_setup:
            ssh_wizard = get_ssh_host_wizard(self.db)
            return ssh_wizard.validate_step_data(wizard, step_data)
        
        # Default validation
        if not step_data:
            raise ValidationError("Step data cannot be empty")
    
    def _is_step_complete(self, wizard: WizardInstance) -> bool:
        """Check if current step has required data"""
        # This would check wizard-specific requirements
        # For now, simplified check
        return True
    
    async def _run_step_test(self, wizard: WizardInstance, test_type: str) -> Dict[str, Any]:
        """Run test for current step"""
        if wizard.wizard_type == WizardType.ssh_host_setup:
            ssh_wizard = get_ssh_host_wizard(self.db)
            return await ssh_wizard.run_step_test(wizard, test_type)
        
        # Default test response
        return {"success": True, "message": "Test not implemented for this wizard type"}
    
    async def _complete_wizard_actions(self, wizard: WizardInstance) -> Dict[str, Any]:
        """Perform final actions when wizard is completed"""
        if wizard.wizard_type == WizardType.ssh_host_setup:
            # Import here to avoid circular imports
            from app.models.docker_host import DockerHost, HostCredential, HostTag, UserHostPermission, HostStatus, HostType, ConnectionType
            from app.services.encryption import get_encryption_service
            
            encryption = get_encryption_service()
            state = wizard.state
            
            # Log state for debugging
            logger.info(f"Wizard state during completion: {state}")
            
            # Determine host type
            host_type = state.get("host_type", "standalone")
            if host_type == "swarm_manager":
                host_type = HostType.swarm_manager
            elif host_type == "swarm_worker":
                host_type = HostType.swarm_worker
            else:
                host_type = HostType.standalone
            
            # Create host
            host = DockerHost(
                name=state["connection_name"],
                display_name=state.get("display_name"),
                description=state.get("description"),
                host_type=host_type,
                connection_type=ConnectionType.ssh,
                host_url=state["host_url"],
                is_active=True,
                is_default=state.get("is_default", False),
                status=HostStatus.setup_pending
            )
            
            self.db.add(host)
            await self.db.flush()
            
            # Store credentials
            auth_method = state.get("auth_method")
            
            if auth_method in ["existing_key", "new_key"]:
                if state.get("private_key"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_private_key",
                        encrypted_value=encryption.encrypt(state["private_key"])
                    )
                    self.db.add(cred)
                
                if state.get("key_passphrase"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_private_key_passphrase",
                        encrypted_value=encryption.encrypt(state["key_passphrase"])
                    )
                    self.db.add(cred)
            
            elif auth_method == "password":
                if state.get("password"):
                    cred = HostCredential(
                        host_id=host.id,
                        credential_type="ssh_password",
                        encrypted_value=encryption.encrypt(state["password"])
                    )
                    self.db.add(cred)
            
            # Add user permission
            permission = UserHostPermission(
                user_id=wizard.user_id,
                host_id=host.id,
                permission_level="admin"
            )
            self.db.add(permission)
            
            # Add tags if provided
            tags = state.get("tags", [])
            for tag_name in tags:
                if tag_name:
                    tag = HostTag(
                        host_id=host.id,
                        tag_name=tag_name
                    )
                    self.db.add(tag)
            
            # Don't update wizard here - it will be updated in complete_wizard
            logger.info(f"Created SSH host {host.name} ({host.id}) via wizard")
            
            return {
                "resource_id": str(host.id),
                "resource_type": "docker_host",
                "host_name": host.name
            }
        
        # Default completion
        return {"resource_id": str(wizard.resource_id) if wizard.resource_id else None}
    
    async def _cleanup_wizard(self, wizard: WizardInstance) -> None:
        """Cleanup any temporary resources when wizard is cancelled"""
        # This would contain wizard-specific cleanup logic
        pass


# Factory function
def get_wizard_service(db: AsyncSession) -> WizardService:
    """Get wizard service instance"""
    return WizardService(db)