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
  Select,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  MoreVert as MoreIcon,
  CheckCircle as ActiveIcon,
  PauseCircle as PauseIcon,
  RemoveCircle as DrainIcon,
  Crown as LeaderIcon,
  Computer as NodeIcon,
  Worker as WorkerIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useNodes, useUpdateNode, useRemoveNode } from '../hooks/useNodes';
import { formatDistanceToNow } from 'date-fns';

export default function Nodes() {
  const { hostId } = useParams<{ hostId: string }>();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [availability, setAvailability] = useState<string>('');
  const [role, setRole] = useState<string>('');

  const { data, isLoading, error, refetch } = useNodes(hostId || '');
  const updateNode = useUpdateNode();
  const removeNode = useRemoveNode();

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, node: any) => {
    setAnchorEl(event.currentTarget);
    setSelectedNode(node);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedNode(null);
  };

  const handleUpdateClick = () => {
    if (selectedNode) {
      setAvailability(selectedNode.availability);
      setRole(selectedNode.role);
      setUpdateDialogOpen(true);
    }
    handleMenuClose();
  };

  const handleRemoveClick = () => {
    setRemoveDialogOpen(true);
    handleMenuClose();
  };

  const handleUpdateNode = async () => {
    if (!hostId || !selectedNode) return;

    const updates: any = {};
    if (availability !== selectedNode.availability) {
      updates.availability = availability;
    }
    if (role !== selectedNode.role) {
      updates.role = role;
    }

    try {
      await updateNode.mutateAsync({
        hostId,
        nodeId: selectedNode.id,
        version: selectedNode.version,
        update: updates,
      });
      setUpdateDialogOpen(false);
      setSelectedNode(null);
    } catch (error) {
      console.error('Failed to update node:', error);
    }
  };

  const handleRemoveNode = async (force: boolean) => {
    if (!hostId || !selectedNode) return;

    try {
      await removeNode.mutateAsync({
        hostId,
        nodeId: selectedNode.id,
        force,
      });
      setRemoveDialogOpen(false);
      setSelectedNode(null);
    } catch (error) {
      console.error('Failed to remove node:', error);
    }
  };

  const getAvailabilityIcon = (availability: string) => {
    switch (availability) {
      case 'active':
        return <ActiveIcon color="success" fontSize="small" />;
      case 'pause':
        return <PauseIcon color="warning" fontSize="small" />;
      case 'drain':
        return <DrainIcon color="error" fontSize="small" />;
      default:
        return null;
    }
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'ready':
        return <Chip label="Ready" color="success" size="small" />;
      case 'down':
        return <Chip label="Down" color="error" size="small" />;
      case 'unknown':
        return <Chip label="Unknown" color="default" size="small" />;
      default:
        return <Chip label={status} size="small" />;
    }
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
        <Alert severity="error">Failed to load nodes: {error.message}</Alert>
      </Box>
    );
  }

  const nodes = data?.nodes || [];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          <NodeIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
          Swarm Nodes
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
            onClick={() => navigate(`/hosts/${hostId}/swarm/join`)}
          >
            Add Node
          </Button>
        </Box>
      </Box>

      <Card>
        <CardContent>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Hostname</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Availability</TableCell>
                  <TableCell>Engine Version</TableCell>
                  <TableCell>IP Address</TableCell>
                  <TableCell>Last Updated</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {nodes.map((node) => (
                  <TableRow key={node.id}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {node.hostname}
                        {node.is_leader && (
                          <Tooltip title="Leader">
                            <LeaderIcon sx={{ ml: 1, color: 'warning.main', fontSize: 20 }} />
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {node.role === 'manager' ? (
                          <>
                            <LeaderIcon sx={{ mr: 0.5, fontSize: 18 }} />
                            Manager
                          </>
                        ) : (
                          <>
                            <WorkerIcon sx={{ mr: 0.5, fontSize: 18 }} />
                            Worker
                          </>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>{getStatusChip(node.state)}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        {getAvailabilityIcon(node.availability)}
                        <Typography variant="body2" sx={{ ml: 0.5 }}>
                          {node.availability}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{node.engine_version || '-'}</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {node.addr}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(node.updated_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={(e) => handleMenuOpen(e, node)}
                      >
                        <MoreIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleUpdateClick}>Update Node</MenuItem>
        <MenuItem onClick={handleRemoveClick}>Remove Node</MenuItem>
      </Menu>

      {/* Update Node Dialog */}
      <Dialog open={updateDialogOpen} onClose={() => setUpdateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Update Node</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Availability</InputLabel>
              <Select
                value={availability}
                onChange={(e) => setAvailability(e.target.value)}
                label="Availability"
              >
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="pause">Pause</MenuItem>
                <MenuItem value="drain">Drain</MenuItem>
              </Select>
            </FormControl>

            {selectedNode?.role === 'worker' && (
              <FormControl fullWidth>
                <InputLabel>Role</InputLabel>
                <Select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  label="Role"
                >
                  <MenuItem value="worker">Worker</MenuItem>
                  <MenuItem value="manager">Manager</MenuItem>
                </Select>
              </FormControl>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpdateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleUpdateNode}
            disabled={updateNode.isPending}
          >
            {updateNode.isPending ? 'Updating...' : 'Update'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Remove Node Dialog */}
      <Dialog open={removeDialogOpen} onClose={() => setRemoveDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Remove Node</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will remove the node from the swarm. Any tasks running on this node will be rescheduled.
          </Alert>
          <Typography>
            Are you sure you want to remove node <strong>{selectedNode?.hostname}</strong>?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveDialogOpen(false)}>Cancel</Button>
          <Button
            color="warning"
            onClick={() => handleRemoveNode(false)}
            disabled={removeNode.isPending}
          >
            Remove
          </Button>
          <Button
            color="error"
            onClick={() => handleRemoveNode(true)}
            disabled={removeNode.isPending}
          >
            Force Remove
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}