package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var (
	// Version information (set during build)
	Version   = "0.1.0"
	GitCommit = "unknown"
	BuildDate = "unknown"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print version information",
	Long:  `Display version information about docker-swarm-ctl`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("docker-swarm-ctl version %s\n", Version)
		fmt.Printf("  Git commit: %s\n", GitCommit)
		fmt.Printf("  Built:      %s\n", BuildDate)
	},
}