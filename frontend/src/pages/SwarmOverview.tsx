import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Alert,
  AlertTitle,
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Tooltip,
  Paper,
  Divider,
} from '@mui/material';
import {
  CloudQueue as CloudIcon,
  Computer as NodeIcon,
  Apps as ServiceIcon,
  Security as SecurityIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  ExitToApp as LeaveIcon,
  VpnKey as KeyIcon,
} from '@mui/icons-material';
import { useSwarmInfo, useSwarmInit, useSwarmLeave } from '../hooks/useSwarm';
import { useNodes } from '../hooks/useNodes';
import { useServices } from '../hooks/useServices';
import { formatDistanceToNow } from 'date-fns';

export default function SwarmOverview() {
  const { hostId } = useParams<{ hostId: string }>();
  const navigate = useNavigate();
  const [initDialogOpen, setInitDialogOpen] = useState(false);
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [advertiseAddr, setAdvertiseAddr] = useState('');
  
  const { data: swarmInfo, isLoading: swarmLoading, error: swarmError } = useSwarmInfo(hostId || '');
  const { data: nodesData, isLoading: nodesLoading } = useNodes(hostId || '');
  const { data: servicesData, isLoading: servicesLoading } = useServices(hostId || '');
  
  const swarmInit = useSwarmInit();
  const swarmLeave = useSwarmLeave();
  
  const isNotInSwarm = swarmError?.response?.status === 400;
  
  const handleInitSwarm = async () => {
    if (!hostId || !advertiseAddr) return;
    
    try {
      await swarmInit.mutateAsync({
        hostId,
        data: { advertise_addr: advertiseAddr }
      });
      setInitDialogOpen(false);
      setAdvertiseAddr('');
    } catch (error) {
      console.error('Failed to initialize swarm:', error);
    }
  };
  
  const handleLeaveSwarm = async (force: boolean) => {
    if (!hostId) return;
    
    try {
      await swarmLeave.mutateAsync({ hostId, force });
      setLeaveDialogOpen(false);
    } catch (error) {
      console.error('Failed to leave swarm:', error);
    }
  };
  
  if (!hostId) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No host ID provided</Alert>
      </Box>
    );
  }
  
  if (swarmLoading || nodesLoading || servicesLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  const nodes = nodesData?.nodes || [];
  const services = servicesData?.services || [];
  const managerNodes = nodes.filter(n => n.role === 'manager');
  const workerNodes = nodes.filter(n => n.role === 'worker');
  const readyNodes = nodes.filter(n => n.state === 'ready');
  const runningServices = services.filter(s => s.UpdateStatus?.State !== 'paused');
  
  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          <CloudIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
          Docker Swarm
        </Typography>
        <Box>
          {!isNotInSwarm && (
            <Tooltip title="Refresh">
              <IconButton onClick={() => window.location.reload()}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>
      
      {isNotInSwarm ? (
        <Card>
          <CardContent>
            <Alert severity="info" sx={{ mb: 2 }}>
              <AlertTitle>Not Part of a Swarm</AlertTitle>
              This Docker host is not currently part of a swarm cluster.
            </Alert>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setInitDialogOpen(true)}
              >
                Initialize New Swarm
              </Button>
              <Button
                variant="outlined"
                onClick={() => navigate(`/hosts/${hostId}/join-swarm`)}
              >
                Join Existing Swarm
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Swarm Info Card */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Swarm Information</Typography>
                <Box>
                  <Tooltip title="Manage Tokens">
                    <IconButton size="small" onClick={() => navigate(`/swarm/${hostId}/tokens`)}>
                      <KeyIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Swarm Settings">
                    <IconButton size="small" onClick={() => navigate(`/swarm/${hostId}/settings`)}>
                      <SettingsIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Leave Swarm">
                    <IconButton size="small" color="error" onClick={() => setLeaveDialogOpen(true)}>
                      <LeaveIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Swarm ID</Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', mb: 1 }}>
                    {swarmInfo?.ID}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" color="text.secondary">Created</Typography>
                  <Typography variant="body1">
                    {swarmInfo?.CreatedAt && formatDistanceToNow(new Date(swarmInfo.CreatedAt), { addSuffix: true })}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
          
          {/* Stats Grid */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <NodeIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                <Typography variant="h4">{nodes.length}</Typography>
                <Typography color="text.secondary">Total Nodes</Typography>
                <Box sx={{ mt: 1 }}>
                  <Chip label={`${managerNodes.length} Managers`} size="small" sx={{ mr: 0.5 }} />
                  <Chip label={`${workerNodes.length} Workers`} size="small" />
                </Box>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <NodeIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                <Typography variant="h4">{readyNodes.length}</Typography>
                <Typography color="text.secondary">Ready Nodes</Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {((readyNodes.length / nodes.length) * 100).toFixed(0)}% Healthy
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <ServiceIcon sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
                <Typography variant="h4">{services.length}</Typography>
                <Typography color="text.secondary">Services</Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {runningServices.length} Running
                </Typography>
              </Paper>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <SecurityIcon sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
                <Typography variant="h4">TLS</Typography>
                <Typography color="text.secondary">Security</Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Enabled
                </Typography>
              </Paper>
            </Grid>
          </Grid>
          
          {/* Quick Actions */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Quick Actions</Typography>
              <Grid container spacing={2}>
                <Grid item>
                  <Button
                    variant="contained"
                    startIcon={<ServiceIcon />}
                    onClick={() => navigate(`/hosts/${hostId}/services/create`)}
                  >
                    Create Service
                  </Button>
                </Grid>
                <Grid item>
                  <Button
                    variant="outlined"
                    startIcon={<NodeIcon />}
                    onClick={() => navigate(`/hosts/${hostId}/nodes`)}
                  >
                    Manage Nodes
                  </Button>
                </Grid>
                <Grid item>
                  <Button
                    variant="outlined"
                    onClick={() => navigate(`/hosts/${hostId}/services`)}
                  >
                    View Services
                  </Button>
                </Grid>
                <Grid item>
                  <Button
                    variant="outlined"
                    onClick={() => navigate(`/hosts/${hostId}/secrets-configs`)}
                  >
                    Secrets & Configs
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </>
      )}
      
      {/* Initialize Swarm Dialog */}
      <Dialog open={initDialogOpen} onClose={() => setInitDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Initialize Docker Swarm</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will initialize a new swarm with this host as the first manager node.
          </Alert>
          <TextField
            fullWidth
            label="Advertise Address"
            value={advertiseAddr}
            onChange={(e) => setAdvertiseAddr(e.target.value)}
            helperText="The address that will be advertised to other nodes for API access (e.g., 192.168.1.100:2377)"
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInitDialogOpen(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleInitSwarm}
            disabled={!advertiseAddr || swarmInit.isPending}
          >
            {swarmInit.isPending ? 'Initializing...' : 'Initialize Swarm'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Leave Swarm Dialog */}
      <Dialog open={leaveDialogOpen} onClose={() => setLeaveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Leave Swarm</DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Warning</AlertTitle>
            Leaving the swarm will remove this node from the cluster. Services running on this node will be rescheduled to other nodes.
          </Alert>
          <Typography>
            Are you sure you want to leave the swarm?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLeaveDialogOpen(false)}>Cancel</Button>
          <Button 
            color="warning"
            onClick={() => handleLeaveSwarm(false)}
            disabled={swarmLeave.isPending}
          >
            Leave Swarm
          </Button>
          <Button 
            color="error"
            onClick={() => handleLeaveSwarm(true)}
            disabled={swarmLeave.isPending}
          >
            Force Leave
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}