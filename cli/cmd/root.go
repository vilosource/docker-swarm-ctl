package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/docker-swarm-ctl/cli/pkg/client"
	"github.com/docker-swarm-ctl/cli/pkg/config"
)

var (
	cfgFile      string
	outputFormat string
	contextName  string
	cfg          *config.Config
	apiClient    *client.Client
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "docker-swarm-ctl",
	Short: "kubectl-like CLI for Docker Swarm management",
	Long: `Docker Swarm Control is a command-line tool for managing Docker Swarm clusters
across multiple hosts. It provides a kubectl-like interface for Docker Swarm operations.`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute() error {
	return rootCmd.Execute()
}

func init() {
	cobra.OnInitialize(initConfig)

	// Global flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.docker-swarm-ctl/config.yaml)")
	rootCmd.PersistentFlags().StringVar(&contextName, "context", "", "override current context")
	rootCmd.PersistentFlags().StringVarP(&outputFormat, "output", "o", "table", "output format (table, json, yaml, wide)")

	// Add subcommands
	rootCmd.AddCommand(authCmd)
	rootCmd.AddCommand(configCmd)
	rootCmd.AddCommand(getCmd)
	rootCmd.AddCommand(createCmd)
	rootCmd.AddCommand(deleteCmd)
	rootCmd.AddCommand(scaleCmd)
	rootCmd.AddCommand(logsCmd)
	rootCmd.AddCommand(execCmd)
	rootCmd.AddCommand(versionCmd)
}

// initConfig reads in config file and ENV variables if set.
func initConfig() {
	if cfgFile != "" {
		// Use config file from the flag.
		viper.SetConfigFile(cfgFile)
	} else {
		// Find home directory.
		home, err := os.UserHomeDir()
		cobra.CheckErr(err)

		// Search config in home directory with name ".docker-swarm-ctl" (without extension).
		configPath := filepath.Join(home, ".docker-swarm-ctl")
		viper.AddConfigPath(configPath)
		viper.SetConfigType("yaml")
		viper.SetConfigName("config")

		// Create config directory if it doesn't exist
		if err := os.MkdirAll(configPath, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "Error creating config directory: %v\n", err)
		}
	}

	viper.AutomaticEnv() // read in environment variables that match

	// Load configuration
	cfg = config.New()
	if err := viper.ReadInConfig(); err == nil {
		if err := viper.Unmarshal(cfg); err != nil {
			fmt.Fprintf(os.Stderr, "Error parsing config file: %v\n", err)
		}
	}

	// Override context if specified
	if contextName != "" {
		cfg.CurrentContext = contextName
	}

	// Initialize API client if we have a current context
	if cfg.CurrentContext != "" {
		if ctx, ok := cfg.Contexts[cfg.CurrentContext]; ok {
			apiClient = client.New(ctx.APIUrl, ctx.Token)
		}
	}
}

// Helper function to require authentication
func requireAuth() error {
	if apiClient == nil || apiClient.Token == "" {
		return fmt.Errorf("not authenticated. Please run 'docker-swarm-ctl login' first")
	}
	return nil
}

// Helper function to require host parameter
func requireHost(cmd *cobra.Command) (string, error) {
	host, _ := cmd.Flags().GetString("host")
	if host == "" {
		return "", fmt.Errorf("--host flag is required")
	}
	return host, nil
}