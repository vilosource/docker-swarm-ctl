package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
)

var execCmd = &cobra.Command{
	Use:   "exec CONTAINER COMMAND [ARG...]",
	Short: "Execute a command in a container",
	Long: `Execute a command in a running container.

Examples:
  # Execute bash in a container
  docker-swarm-ctl exec nginx-abc123 --host <host-id> -- /bin/bash

  # Execute a command with arguments
  docker-swarm-ctl exec nginx-abc123 --host <host-id> -- ls -la /etc/nginx`,
	Args: cobra.MinimumNArgs(2),
	RunE: func(cmd *cobra.Command, args []string) error {
		containerID := args[0]
		command := strings.Join(args[1:], " ")
		
		hostID, err := requireHost(cmd)
		if err != nil {
			return err
		}

		return fmt.Errorf("executing command in container %s on host %s not yet implemented (command: %s)",
			containerID, hostID, command)
	},
}

func init() {
	execCmd.Flags().String("host", "", "Host ID (required)")
	execCmd.MarkFlagRequired("host")
}