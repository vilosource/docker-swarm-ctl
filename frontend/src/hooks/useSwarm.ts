import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export interface SwarmInfo {
  ID: string;
  CreatedAt: string;
  UpdatedAt: string;
  Spec: {
    Name?: string;
    Labels: Record<string, string>;
  };
  Version: {
    Index: number;
  };
  JoinTokens: {
    Worker: string;
    Manager: string;
  };
  RootCACert: string;
}

export interface SwarmInit {
  advertise_addr: string;
  listen_addr?: string;
  force_new_cluster?: boolean;
}

export interface SwarmJoin {
  remote_addrs: string[];
  join_token: string;
  advertise_addr?: string;
  listen_addr?: string;
}

// Get swarm info
export const useSwarmInfo = (hostId: string) => {
  return useQuery<SwarmInfo>({
    queryKey: ['swarm', hostId],
    queryFn: async () => {
      const response = await api.get(`/swarm/`, { params: { host_id: hostId } });
      return response.data;
    },
    enabled: !!hostId,
    retry: (failureCount, error: any) => {
      // Don't retry if host is not in a swarm
      if (error?.response?.status === 400) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

// Initialize swarm
export const useSwarmInit = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ hostId, data }: { hostId: string; data: SwarmInit }) => {
      const response = await api.post(`/swarm/init`, data, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['swarm', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
  });
};

// Join swarm
export const useSwarmJoin = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ hostId, data }: { hostId: string; data: SwarmJoin }) => {
      const response = await api.post(`/swarm/join`, data, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['swarm', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
  });
};

// Leave swarm
export const useSwarmLeave = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ hostId, force = false }: { hostId: string; force?: boolean }) => {
      const response = await api.post(`/swarm/leave`, { force }, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['swarm', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
  });
};

// Update swarm
export const useSwarmUpdate = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      version,
      rotateWorkerToken = false,
      rotateManagerToken = false,
      rotateManagerUnlockKey = false 
    }: { 
      hostId: string;
      version: number;
      rotateWorkerToken?: boolean;
      rotateManagerToken?: boolean;
      rotateManagerUnlockKey?: boolean;
    }) => {
      const response = await api.put(`/swarm/`, {
        version,
        rotate_worker_token: rotateWorkerToken,
        rotate_manager_token: rotateManagerToken,
        rotate_manager_unlock_key: rotateManagerUnlockKey,
      }, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['swarm', variables.hostId] });
    },
  });
};