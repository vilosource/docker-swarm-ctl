import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface Node {
  ID: string;
  Version: {
    Index: number;
  };
  CreatedAt: string;
  UpdatedAt: string;
  Spec: {
    Name?: string;
    Labels: Record<string, string>;
    Role: 'worker' | 'manager';
    Availability: 'active' | 'pause' | 'drain';
  };
  Description: {
    Hostname: string;
    Platform: {
      Architecture: string;
      OS: string;
    };
    Resources: {
      NanoCPUs: number;
      MemoryBytes: number;
    };
    Engine: {
      EngineVersion: string;
    };
  };
  Status: {
    State: 'unknown' | 'down' | 'ready' | 'disconnected';
    Message?: string;
    Addr?: string;
  };
  ManagerStatus?: {
    Leader: boolean;
    Reachability: 'unknown' | 'unreachable' | 'reachable';
    Addr: string;
  };
  // Computed fields
  hostname: string;
  role: 'worker' | 'manager';
  availability: 'active' | 'pause' | 'drain';
  state: string;
  addr?: string;
  engine_version: string;
}

export interface NodeUpdate {
  version: number;
  spec: {
    Name?: string;
    Labels?: Record<string, string>;
    Role?: 'worker' | 'manager';
    Availability?: 'active' | 'pause' | 'drain';
  };
}

// List nodes
export const useNodes = (hostId: string, role?: string) => {
  return useQuery<{ nodes: Node[]; total: number }>({
    queryKey: ['nodes', hostId, role],
    queryFn: async () => {
      const params: any = { host_id: hostId };
      if (role) params.role = role;
      
      const response = await api.get('/nodes/', { params });
      return response.data;
    },
    enabled: !!hostId,
  });
};

// Get single node
export const useNode = (hostId: string, nodeId: string) => {
  return useQuery<Node>({
    queryKey: ['nodes', hostId, nodeId],
    queryFn: async () => {
      const response = await api.get(`/nodes/${nodeId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId && !!nodeId,
  });
};

// Update node
export const useUpdateNode = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      nodeId, 
      update 
    }: { 
      hostId: string; 
      nodeId: string; 
      update: NodeUpdate;
    }) => {
      const response = await api.put(`/nodes/${nodeId}`, update, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['nodes', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['nodes', variables.hostId, variables.nodeId] });
    },
  });
};

// Remove node
export const useRemoveNode = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      nodeId, 
      force = false 
    }: { 
      hostId: string; 
      nodeId: string; 
      force?: boolean;
    }) => {
      const response = await api.delete(`/nodes/${nodeId}`, { 
        params: { host_id: hostId, force } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['nodes', variables.hostId] });
    },
  });
};