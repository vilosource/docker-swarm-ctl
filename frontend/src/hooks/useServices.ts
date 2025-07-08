import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export interface ServicePort {
  Protocol: string;
  TargetPort: number;
  PublishedPort?: number;
  PublishMode: string;
}

export interface Service {
  ID: string;
  Version: {
    Index: number;
  };
  CreatedAt: string;
  UpdatedAt: string;
  Spec: any; // Complex spec object
  Endpoint?: {
    Spec?: any;
    Ports?: ServicePort[];
    VirtualIPs?: Array<{ NetworkID: string; Addr: string }>;
  };
  UpdateStatus?: {
    State: string;
    StartedAt?: string;
    CompletedAt?: string;
    Message?: string;
  };
  // Computed fields
  name: string;
  image: string;
  mode: 'replicated' | 'global';
  replicas?: number;
}

export interface ServiceCreate {
  name: string;
  image: string;
  command?: string[];
  env?: string[];
  replicas?: number;
  ports?: Array<{
    Protocol?: string;
    TargetPort: number;
    PublishedPort?: number;
    PublishMode?: string;
  }>;
  mounts?: Array<{
    Type: string;
    Source?: string;
    Target: string;
    ReadOnly?: boolean;
  }>;
  networks?: string[];
  labels?: Record<string, string>;
  constraints?: string[];
  cpu_limit?: number;
  memory_limit?: number;
  cpu_reservation?: number;
  memory_reservation?: number;
}

export interface Task {
  ID: string;
  Version: {
    Index: number;
  };
  CreatedAt: string;
  UpdatedAt: string;
  Name?: string;
  Labels: Record<string, string>;
  Spec: any;
  ServiceID: string;
  Slot?: number;
  NodeID?: string;
  Status: {
    Timestamp: string;
    State: string;
    Message?: string;
    Err?: string;
    ContainerStatus?: {
      ContainerID?: string;
    };
  };
  DesiredState: string;
  // Computed fields
  container_id?: string;
  state: string;
}

// List services
export const useServices = (hostId: string, label?: string) => {
  return useQuery<{ services: Service[]; total: number }>({
    queryKey: ['services', hostId, label],
    queryFn: async () => {
      const params: any = { host_id: hostId };
      if (label) params.label = label;
      
      const response = await api.get('/services/', { params });
      return response.data;
    },
    enabled: !!hostId,
  });
};

// Get single service
export const useService = (hostId: string, serviceId: string) => {
  return useQuery<Service>({
    queryKey: ['services', hostId, serviceId],
    queryFn: async () => {
      const response = await api.get(`/services/${serviceId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId && !!serviceId,
  });
};

// Create service
export const useCreateService = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      data 
    }: { 
      hostId: string; 
      data: ServiceCreate;
    }) => {
      const response = await api.post('/services/', data, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId] });
    },
  });
};

// Update service
export const useUpdateService = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      serviceId,
      version,
      update 
    }: { 
      hostId: string; 
      serviceId: string;
      version: number;
      update: Partial<ServiceCreate> & { force_update?: boolean };
    }) => {
      const response = await api.put(`/services/${serviceId}`, 
        { version, ...update }, 
        { params: { host_id: hostId } }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId, variables.serviceId] });
    },
  });
};

// Scale service
export const useScaleService = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      serviceId,
      replicas 
    }: { 
      hostId: string; 
      serviceId: string;
      replicas: number;
    }) => {
      const response = await api.post(`/services/${serviceId}/scale`, 
        { replicas }, 
        { params: { host_id: hostId } }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId] });
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId, variables.serviceId] });
    },
  });
};

// Remove service
export const useRemoveService = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ 
      hostId, 
      serviceId 
    }: { 
      hostId: string; 
      serviceId: string;
    }) => {
      const response = await api.delete(`/services/${serviceId}`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['services', variables.hostId] });
    },
  });
};

// Get service tasks
export const useServiceTasks = (hostId: string, serviceId: string) => {
  return useQuery<{ tasks: Task[]; total: number }>({
    queryKey: ['services', hostId, serviceId, 'tasks'],
    queryFn: async () => {
      const response = await api.get(`/services/${serviceId}/tasks`, { 
        params: { host_id: hostId } 
      });
      return response.data;
    },
    enabled: !!hostId && !!serviceId,
  });
};

// Get service logs
export const useServiceLogs = (hostId: string, serviceId: string, tail = 100, timestamps = false) => {
  return useQuery<{ logs: string }>({
    queryKey: ['services', hostId, serviceId, 'logs', tail, timestamps],
    queryFn: async () => {
      const response = await api.get(`/services/${serviceId}/logs`, { 
        params: { host_id: hostId, tail, timestamps } 
      });
      return response.data;
    },
    enabled: !!hostId && !!serviceId,
  });
};