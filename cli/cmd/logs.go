package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var logsCmd = &cobra.Command{
	Use:   "logs CONTAINER",
	Short: "Print logs of a container",
	Long: `Print the logs for a container.

Examples:
  # Get logs from nginx container
  docker-swarm-ctl logs nginx-abc123 --host <host-id>

  # Follow log output
  docker-swarm-ctl logs nginx-abc123 --host <host-id> --follow`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		containerID := args[0]
		hostID, err := requireHost(cmd)
		if err != nil {
			return err
		}

		follow, _ := cmd.Flags().GetBool("follow")
		tail, _ := cmd.Flags().GetInt("tail")
		timestamps, _ := cmd.Flags().GetBool("timestamps")

		return fmt.Errorf("getting logs for container %s on host %s not yet implemented (follow=%v, tail=%d, timestamps=%v)",
			containerID, hostID, follow, tail, timestamps)
	},
}

func init() {
	logsCmd.Flags().String("host", "", "Host ID (required)")
	logsCmd.Flags().BoolP("follow", "f", false, "Follow log output")
	logsCmd.Flags().Int("tail", 100, "Number of lines to show from the end")
	logsCmd.Flags().BoolP("timestamps", "t", false, "Show timestamps")
	logsCmd.MarkFlagRequired("host")
}