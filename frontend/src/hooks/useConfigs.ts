import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface Config {
  ID: string;
  Version: {
    Index: number;
  };
  CreatedAt: string;
  UpdatedAt: string;
  Spec: {
    Name: string;
    Labels?: Record<string, string>;
  };
}

export interface ConfigCreate {
  name: string;
  data: string; // Base64 encoded
  labels?: Record<string, string>;
}

// List configs
export const useConfigs = (hostId: string) => {
  return useQuery<{ configs: Config[]; total: number }>({
    queryKey: ['configs', hostId],
    queryFn: async () => {
      const response = await api.get('/configs/', { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId,
  });
};

// Get single config
export const useConfig = (hostId: string, configId: string) => {
  return useQuery<Config>({
    queryKey: ['configs', hostId, configId],
    queryFn: async () => {
      const response = await api.get(`/configs/${configId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId && !!configId,
  });
};

// Create config
export const useCreateConfig = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      data 
    }: { 
      hostId: string; 
      data: ConfigCreate;
    }) => {
      const response = await api.post('/configs/', data, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['configs', variables.hostId] });
    },
  });
};

// Remove config
export const useRemoveConfig = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      configId 
    }: { 
      hostId: string; 
      configId: string;
    }) => {
      const response = await api.delete(`/configs/${configId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['configs', variables.hostId] });
    },
  });
};