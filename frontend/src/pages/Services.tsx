import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  LinearProgress,
  Stack,
} from '@mui/material';
import {
  MoreVert as MoreIcon,
  Apps as ServiceIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  Scale as ScaleIcon,
  Logs as LogsIcon,
  Task as TaskIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Pause as PauseIcon,
  PlayArrow as ResumeIcon,
} from '@mui/icons-material';
import { useServices, useScaleService, useRemoveService } from '../hooks/useServices';
import { formatDistanceToNow } from 'date-fns';

export default function Services() {
  const { hostId } = useParams<{ hostId: string }>();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedService, setSelectedService] = useState<any>(null);
  const [scaleDialogOpen, setScaleDialogOpen] = useState(false);
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [replicas, setReplicas] = useState<number>(1);

  const { data, isLoading, error, refetch } = useServices(hostId || '');
  const scaleService = useScaleService();
  const removeService = useRemoveService();

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, service: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedService(service);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedService(null);
  };

  const handleScaleClick = () => {
    if (selectedService) {
      setReplicas(selectedService.replicas || 1);
      setScaleDialogOpen(true);
    }
    handleMenuClose();
  };

  const handleEditClick = () => {
    if (selectedService) {
      navigate(`/hosts/${hostId}/services/${selectedService.ID}/edit`);
    }
    handleMenuClose();
  };

  const handleLogsClick = () => {
    if (selectedService) {
      navigate(`/hosts/${hostId}/services/${selectedService.ID}/logs`);
    }
    handleMenuClose();
  };

  const handleTasksClick = () => {
    if (selectedService) {
      navigate(`/hosts/${hostId}/services/${selectedService.ID}/tasks`);
    }
    handleMenuClose();
  };

  const handleRemoveClick = () => {
    setRemoveDialogOpen(true);
    handleMenuClose();
  };

  const handleScale = async () => {
    if (!hostId || !selectedService) return;

    try {
      await scaleService.mutateAsync({
        hostId,
        serviceId: selectedService.ID,
        replicas,
      });
      setScaleDialogOpen(false);
      setSelectedService(null);
    } catch (error) {
      console.error('Failed to scale service:', error);
    }
  };

  const handleRemove = async () => {
    if (!hostId || !selectedService) return;

    try {
      await removeService.mutateAsync({
        hostId,
        serviceId: selectedService.ID,
      });
      setRemoveDialogOpen(false);
      setSelectedService(null);
    } catch (error) {
      console.error('Failed to remove service:', error);
    }
  };

  const getStatusChip = (service: any) => {
    if (service.UpdateStatus?.State === 'updating') {
      return <Chip label="Updating" color="warning" size="small" />;
    }
    if (service.UpdateStatus?.State === 'paused') {
      return <Chip label="Paused" color="default" size="small" />;
    }
    return <Chip label="Running" color="success" size="small" />;
  };

  const getReplicaStatus = (service: any) => {
    if (service.mode !== 'replicated') {
      return <Chip label="Global" size="small" variant="outlined" />;
    }
    
    const running = service.runningTasks || 0;
    const desired = service.replicas || 0;
    
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2">
          {running}/{desired}
        </Typography>
        {running < desired && (
          <Tooltip title={`${desired - running} replicas starting`}>
            <CircularProgress size={16} />
          </Tooltip>
        )}
      </Box>
    );
  };

  const getServicePorts = (service: any) => {
    const ports = service.Endpoint?.Ports || [];
    if (ports.length === 0) return '-';
    
    return ports.map((port: any) => (
      <Chip
        key={`${port.TargetPort}-${port.PublishedPort}`}
        label={`${port.PublishedPort || '?'}:${port.TargetPort}/${port.Protocol}`}
        size="small"
        variant="outlined"
        sx={{ mr: 0.5 }}
      />
    ));
  };

  if (!hostId) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No host ID provided</Alert>
      </Box>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load services: {error.message}</Alert>
      </Box>
    );
  }

  const services = data?.services || [];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          <ServiceIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
          Services
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetch()}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate(`/hosts/${hostId}/services/create`)}
          >
            Create Service
          </Button>
        </Box>
      </Box>

      <Card>
        <CardContent>
          {services.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary" gutterBottom>
                No services running
              </Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => navigate(`/hosts/${hostId}/services/create`)}
              >
                Create your first service
              </Button>
            </Box>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Image</TableCell>
                    <TableCell>Mode</TableCell>
                    <TableCell>Replicas</TableCell>
                    <TableCell>Ports</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Updated</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {services.map((service) => (
                    <TableRow key={service.ID}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {service.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {service.image}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" textTransform="capitalize">
                          {service.mode}
                        </Typography>
                      </TableCell>
                      <TableCell>{getReplicaStatus(service)}</TableCell>
                      <TableCell>{getServicePorts(service)}</TableCell>
                      <TableCell>{getStatusChip(service)}</TableCell>
                      <TableCell>
                        {service.UpdatedAt && 
                          formatDistanceToNow(new Date(service.UpdatedAt), { addSuffix: true })
                        }
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuOpen(e, service)}
                        >
                          <MoreIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        {selectedService?.mode === 'replicated' && (
          <MenuItem onClick={handleScaleClick}>
            <ScaleIcon sx={{ mr: 1, fontSize: 20 }} />
            Scale Service
          </MenuItem>
        )}
        <MenuItem onClick={handleLogsClick}>
          <LogsIcon sx={{ mr: 1, fontSize: 20 }} />
          View Logs
        </MenuItem>
        <MenuItem onClick={handleTasksClick}>
          <TaskIcon sx={{ mr: 1, fontSize: 20 }} />
          View Tasks
        </MenuItem>
        <MenuItem onClick={handleEditClick}>
          <EditIcon sx={{ mr: 1, fontSize: 20 }} />
          Edit Service
        </MenuItem>
        <MenuItem onClick={handleRemoveClick} sx={{ color: 'error.main' }}>
          <DeleteIcon sx={{ mr: 1, fontSize: 20 }} />
          Remove Service
        </MenuItem>
      </Menu>

      {/* Scale Service Dialog */}
      <Dialog open={scaleDialogOpen} onClose={() => setScaleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Scale Service</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <Alert severity="info">
              Scaling will gradually update the service to the desired number of replicas.
            </Alert>
            <TextField
              fullWidth
              type="number"
              label="Number of Replicas"
              value={replicas}
              onChange={(e) => setReplicas(parseInt(e.target.value) || 0)}
              inputProps={{ min: 0, max: 100 }}
              helperText={`Current: ${selectedService?.replicas || 0} replicas`}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScaleDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleScale}
            disabled={scaleService.isPending}
          >
            {scaleService.isPending ? 'Scaling...' : 'Scale'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Remove Service Dialog */}
      <Dialog open={removeDialogOpen} onClose={() => setRemoveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Remove Service</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will permanently remove the service and stop all its tasks.
          </Alert>
          <Typography>
            Are you sure you want to remove service <strong>{selectedService?.name}</strong>?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveDialogOpen(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleRemove}
            disabled={removeService.isPending}
          >
            {removeService.isPending ? 'Removing...' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}