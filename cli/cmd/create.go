package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var createCmd = &cobra.Command{
	Use:   "create TYPE",
	Short: "Create a resource",
	Long: `Create a resource from a file or stdin.

Resource types:
  - host
  - service, svc
  - secret
  - config

Examples:
  # Create a host
  docker-swarm-ctl create host --name docker-1 --url tcp://192.168.1.100:2376

  # Create a service
  docker-swarm-ctl create service --host <host-id> --name nginx --image nginx:latest`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		resourceType := args[0]

		switch resourceType {
		case "host":
			return fmt.Errorf("host creation not yet implemented")
		case "service", "svc":
			return fmt.Errorf("service creation not yet implemented")
		case "secret":
			return fmt.Errorf("secret creation not yet implemented")
		case "config":
			return fmt.Errorf("config creation not yet implemented")
		default:
			return fmt.Errorf("cannot create resource type: %s", resourceType)
		}
	},
}

func init() {
	createCmd.Flags().String("host", "", "Host ID (required for swarm resources)")
	createCmd.Flags().StringP("file", "f", "", "Filename to use to create the resource")
}