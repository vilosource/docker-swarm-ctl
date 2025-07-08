import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface Secret {
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

export interface SecretCreate {
  name: string;
  data: string; // Base64 encoded
  labels?: Record<string, string>;
}

// List secrets
export const useSecrets = (hostId: string) => {
  return useQuery<{ secrets: Secret[]; total: number }>({
    queryKey: ['secrets', hostId],
    queryFn: async () => {
      const response = await api.get('/secrets/', { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId,
  });
};

// Get single secret
export const useSecret = (hostId: string, secretId: string) => {
  return useQuery<Secret>({
    queryKey: ['secrets', hostId, secretId],
    queryFn: async () => {
      const response = await api.get(`/secrets/${secretId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId && !!secretId,
  });
};

// Create secret
export const useCreateSecret = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      data 
    }: { 
      hostId: string; 
      data: SecretCreate;
    }) => {
      const response = await api.post('/secrets/', data, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['secrets', variables.hostId] });
    },
  });
};

// Remove secret
export const useRemoveSecret = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      secretId 
    }: { 
      hostId: string; 
      secretId: string;
    }) => {
      const response = await api.delete(`/secrets/${secretId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['secrets', variables.hostId] });
    },
  });
};