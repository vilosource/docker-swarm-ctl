package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var deleteCmd = &cobra.Command{
	Use:   "delete TYPE NAME",
	Short: "Delete a resource",
	Long: `Delete a resource by name.

Resource types:
  - host
  - service, svc
  - secret
  - config
  - container

Examples:
  # Delete a host
  docker-swarm-ctl delete host docker-1

  # Delete a service
  docker-swarm-ctl delete service nginx --host <host-id>`,
	Args: cobra.MinimumNArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		resourceType := args[0]
		resourceName := args[1]

		switch resourceType {
		case "host":
			return fmt.Errorf("deleting host %s not yet implemented", resourceName)
		case "service", "svc":
			return fmt.Errorf("deleting service %s not yet implemented", resourceName)
		case "secret":
			return fmt.Errorf("deleting secret %s not yet implemented", resourceName)
		case "config":
			return fmt.Errorf("deleting config %s not yet implemented", resourceName)
		case "container":
			return fmt.Errorf("deleting container %s not yet implemented", resourceName)
		default:
			return fmt.Errorf("cannot delete resource type: %s", resourceType)
		}
	},
}

func init() {
	deleteCmd.Flags().String("host", "", "Host ID (required for swarm resources)")
	deleteCmd.Flags().Bool("force", false, "Force deletion")
}