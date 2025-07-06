from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, BigInteger, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.base import Base


class HostType(str, enum.Enum):
    standalone = "standalone"
    swarm_manager = "swarm_manager"
    swarm_worker = "swarm_worker"


class ConnectionType(str, enum.Enum):
    unix = "unix"
    tcp = "tcp"
    ssh = "ssh"


class HostStatus(str, enum.Enum):
    pending = "pending"
    healthy = "healthy"
    unhealthy = "unhealthy"
    unreachable = "unreachable"


class DockerHost(Base):
    __tablename__ = "docker_hosts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(100), nullable=True)  # Short name for UI display
    description = Column(Text, nullable=True)
    host_type = Column(String(50), nullable=False, default=HostType.standalone)
    connection_type = Column(String(50), nullable=False, default=ConnectionType.unix)
    host_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Swarm specific fields
    swarm_id = Column(String(255), nullable=True)
    cluster_name = Column(String(255), nullable=True)
    is_leader = Column(Boolean, default=False)
    
    # Status and metadata
    status = Column(String(50), default=HostStatus.pending)
    last_health_check = Column(DateTime, nullable=True)
    docker_version = Column(String(50), nullable=True)
    api_version = Column(String(50), nullable=True)
    os_type = Column(String(50), nullable=True)
    architecture = Column(String(50), nullable=True)
    
    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    credentials = relationship("HostCredential", back_populates="host", cascade="all, delete-orphan")
    permissions = relationship("UserHostPermission", back_populates="host", cascade="all, delete-orphan")
    tags = relationship("HostTag", back_populates="host", cascade="all, delete-orphan")
    stats = relationship("HostConnectionStats", back_populates="host", cascade="all, delete-orphan")


class HostCredential(Base):
    __tablename__ = "host_credentials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("docker_hosts.id", ondelete="CASCADE"), nullable=False)
    credential_type = Column(String(50), nullable=False)  # tls_cert, tls_key, tls_ca, ssh_key, password
    encrypted_value = Column(Text, nullable=False)
    credential_metadata = Column(JSON, nullable=True)  # Additional info like fingerprints
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    host = relationship("DockerHost", back_populates="credentials")


class UserHostPermission(Base):
    __tablename__ = "user_host_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("docker_hosts.id", ondelete="CASCADE"), nullable=False)
    permission_level = Column(String(50), nullable=False)  # viewer, operator, admin
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    host = relationship("DockerHost", back_populates="permissions")
    granter = relationship("User", foreign_keys=[granted_by])


class HostTag(Base):
    __tablename__ = "host_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("docker_hosts.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String(100), nullable=False)
    tag_value = Column(String(255), nullable=True)
    
    # Relationships
    host = relationship("DockerHost", back_populates="tags")


class HostConnectionStats(Base):
    __tablename__ = "host_connection_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("docker_hosts.id", ondelete="CASCADE"), nullable=False)
    active_connections = Column(Integer, default=0)
    total_connections = Column(BigInteger, default=0)
    failed_connections = Column(BigInteger, default=0)
    avg_response_time_ms = Column(Float, nullable=True)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    measured_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    host = relationship("DockerHost", back_populates="stats")