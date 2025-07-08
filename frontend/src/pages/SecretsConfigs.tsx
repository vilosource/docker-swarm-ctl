import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
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
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  VpnKey as SecretIcon,
  Settings as ConfigIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useSecrets, useCreateSecret, useRemoveSecret } from '../hooks/useSecrets';
import { useConfigs, useCreateConfig, useRemoveConfig } from '../hooks/useConfigs';
import { formatDistanceToNow } from 'date-fns';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function SecretsConfigs() {
  const { hostId } = useParams<{ hostId: string }>();
  const [tabValue, setTabValue] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [newItemName, setNewItemName] = useState('');
  const [newItemData, setNewItemData] = useState('');

  const { data: secretsData, isLoading: secretsLoading, refetch: refetchSecrets } = useSecrets(hostId || '');
  const { data: configsData, isLoading: configsLoading, refetch: refetchConfigs } = useConfigs(hostId || '');
  
  const createSecret = useCreateSecret();
  const removeSecret = useRemoveSecret();
  const createConfig = useCreateConfig();
  const removeConfig = useRemoveConfig();

  const isSecrets = tabValue === 0;
  const data = isSecrets ? secretsData : configsData;
  const items = data ? (isSecrets ? data.secrets : data.configs) : [];
  const isLoading = isSecrets ? secretsLoading : configsLoading;

  const handleCreate = async () => {
    if (!hostId || !newItemName || !newItemData) return;

    const encodedData = btoa(newItemData); // Base64 encode

    try {
      if (isSecrets) {
        await createSecret.mutateAsync({
          hostId,
          data: { name: newItemName, data: encodedData }
        });
      } else {
        await createConfig.mutateAsync({
          hostId,
          data: { name: newItemName, data: encodedData }
        });
      }
      setCreateDialogOpen(false);
      setNewItemName('');
      setNewItemData('');
    } catch (error) {
      console.error(`Failed to create ${isSecrets ? 'secret' : 'config'}:`, error);
    }
  };

  const handleDelete = async () => {
    if (!hostId || !selectedItem) return;

    try {
      if (isSecrets) {
        await removeSecret.mutateAsync({
          hostId,
          secretId: selectedItem.ID
        });
      } else {
        await removeConfig.mutateAsync({
          hostId,
          configId: selectedItem.ID
        });
      }
      setDeleteDialogOpen(false);
      setSelectedItem(null);
    } catch (error) {
      console.error(`Failed to delete ${isSecrets ? 'secret' : 'config'}:`, error);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
  };

  if (!hostId) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No host ID provided</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Secrets & Configs
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => isSecrets ? refetchSecrets() : refetchConfigs()}
            sx={{ mr: 2 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create {isSecrets ? 'Secret' : 'Config'}
          </Button>
        </Box>
      </Box>

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab icon={<SecretIcon />} label="Secrets" />
            <Tab icon={<ConfigIcon />} label="Configs" />
          </Tabs>
        </Box>

        <CardContent>
          <TabPanel value={tabValue} index={0}>
            {secretsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : secretsData?.secrets.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography color="text.secondary" gutterBottom>
                  No secrets found
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setCreateDialogOpen(true)}
                >
                  Create your first secret
                </Button>
              </Box>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>ID</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Labels</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {secretsData?.secrets.map((secret) => (
                      <TableRow key={secret.ID}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {secret.Spec.Name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                              {secret.ID.substring(0, 12)}...
                            </Typography>
                            <Tooltip title="Copy full ID">
                              <IconButton size="small" onClick={() => handleCopyId(secret.ID)}>
                                <CopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                        <TableCell>
                          {formatDistanceToNow(new Date(secret.CreatedAt), { addSuffix: true })}
                        </TableCell>
                        <TableCell>
                          {secret.Spec.Labels && Object.keys(secret.Spec.Labels).length > 0 ? (
                            Object.entries(secret.Spec.Labels).map(([key, value]) => (
                              <Chip
                                key={key}
                                label={`${key}: ${value}`}
                                size="small"
                                variant="outlined"
                                sx={{ mr: 0.5 }}
                              />
                            ))
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setSelectedItem(secret);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            {configsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
              </Box>
            ) : configsData?.configs.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography color="text.secondary" gutterBottom>
                  No configs found
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => setCreateDialogOpen(true)}
                >
                  Create your first config
                </Button>
              </Box>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>ID</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell>Labels</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {configsData?.configs.map((config) => (
                      <TableRow key={config.ID}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {config.Spec.Name}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                              {config.ID.substring(0, 12)}...
                            </Typography>
                            <Tooltip title="Copy full ID">
                              <IconButton size="small" onClick={() => handleCopyId(config.ID)}>
                                <CopyIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                        <TableCell>
                          {formatDistanceToNow(new Date(config.CreatedAt), { addSuffix: true })}
                        </TableCell>
                        <TableCell>
                          {config.Spec.Labels && Object.keys(config.Spec.Labels).length > 0 ? (
                            Object.entries(config.Spec.Labels).map(([key, value]) => (
                              <Chip
                                key={key}
                                label={`${key}: ${value}`}
                                size="small"
                                variant="outlined"
                                sx={{ mr: 0.5 }}
                              />
                            ))
                          ) : (
                            '-'
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => {
                              setSelectedItem(config);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </TabPanel>
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create {isSecrets ? 'Secret' : 'Config'}</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Name"
              value={newItemName}
              onChange={(e) => setNewItemName(e.target.value)}
              sx={{ mb: 2 }}
              helperText="A unique name for this resource"
            />
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Data"
              value={newItemData}
              onChange={(e) => setNewItemData(e.target.value)}
              helperText={isSecrets ? 
                "Enter sensitive data that will be encrypted and stored securely" : 
                "Enter configuration data that will be available to services"
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setCreateDialogOpen(false);
            setNewItemName('');
            setNewItemData('');
          }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!newItemName || !newItemData || createSecret.isPending || createConfig.isPending}
          >
            {(createSecret.isPending || createConfig.isPending) ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Delete {isSecrets ? 'Secret' : 'Config'}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. Services using this {isSecrets ? 'secret' : 'config'} may fail.
          </Alert>
          <Typography>
            Are you sure you want to delete <strong>{selectedItem?.Spec.Name}</strong>?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setDeleteDialogOpen(false);
            setSelectedItem(null);
          }}>
            Cancel
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDelete}
            disabled={removeSecret.isPending || removeConfig.isPending}
          >
            {(removeSecret.isPending || removeConfig.isPending) ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}