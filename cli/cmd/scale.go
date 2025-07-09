package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var scaleCmd = &cobra.Command{
	Use:   "scale SERVICE --replicas=COUNT",
	Short: "Scale a service",
	Long: `Scale a service to a specified number of replicas.

Examples:
  # Scale nginx service to 5 replicas
  docker-swarm-ctl scale nginx --host <host-id> --replicas 5`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		serviceName := args[0]
		hostID, err := requireHost(cmd)
		if err != nil {
			return err
		}

		replicas, _ := cmd.Flags().GetInt("replicas")
		if replicas < 0 {
			return fmt.Errorf("replicas must be non-negative")
		}

		return fmt.Errorf("scaling service %s on host %s to %d replicas not yet implemented", 
			serviceName, hostID, replicas)
	},
}

func init() {
	scaleCmd.Flags().String("host", "", "Host ID (required)")
	scaleCmd.Flags().Int("replicas", 1, "Number of replicas")
	scaleCmd.MarkFlagRequired("host")
	scaleCmd.MarkFlagRequired("replicas")
}