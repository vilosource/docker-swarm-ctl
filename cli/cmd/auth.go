package cmd

import (
	"fmt"
	"os"
	"path/filepath"
	"syscall"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/term"

	"github.com/docker-swarm-ctl/cli/pkg/client"
	"github.com/docker-swarm-ctl/cli/pkg/output"
)

var authCmd = &cobra.Command{
	Use:   "auth",
	Short: "Authentication commands",
	Long:  `Manage authentication for Docker Swarm Control`,
}

var loginCmd = &cobra.Command{
	Use:   "login",
	Short: "Login to Docker Swarm Control",
	Long:  `Authenticate with the Docker Swarm Control API`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Get username
		username, _ := cmd.Flags().GetString("username")
		if username == "" {
			fmt.Print("Username: ")
			fmt.Scanln(&username)
		}

		// Get password
		password, _ := cmd.Flags().GetString("password")
		if password == "" {
			fmt.Print("Password: ")
			bytePassword, err := term.ReadPassword(int(syscall.Stdin))
			if err != nil {
				return fmt.Errorf("failed to read password: %w", err)
			}
			password = string(bytePassword)
			fmt.Println() // New line after password
		}

		// Check if we have a current context
		if cfg.CurrentContext == "" {
			return fmt.Errorf("no context configured. Please run 'docker-swarm-ctl config add-context' first")
		}

		ctx, ok := cfg.Contexts[cfg.CurrentContext]
		if !ok {
			return fmt.Errorf("context '%s' not found", cfg.CurrentContext)
		}

		// Create client without token for login
		loginClient := client.New(ctx.APIUrl, "")

		// Attempt login
		if err := loginClient.Login(username, password); err != nil {
			return fmt.Errorf("login failed: %w", err)
		}

		// Update context with username and token
		ctx.Username = username
		ctx.Token = loginClient.Token

		// Save configuration
		configPath := viper.ConfigFileUsed()
		if configPath == "" {
			home, _ := os.UserHomeDir()
			configPath = filepath.Join(home, ".docker-swarm-ctl", "config.yaml")
		}
		
		if err := cfg.Save(configPath); err != nil {
			return fmt.Errorf("failed to save config: %w", err)
		}

		output.Success("Successfully logged in as %s", username)
		output.Info("Context: %s (%s)", cfg.CurrentContext, ctx.APIUrl)

		return nil
	},
}

var logoutCmd = &cobra.Command{
	Use:   "logout",
	Short: "Logout from Docker Swarm Control",
	Long:  `Remove stored authentication credentials`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if cfg.CurrentContext == "" {
			output.Warning("Not logged in")
			return nil
		}

		ctx, ok := cfg.Contexts[cfg.CurrentContext]
		if !ok || ctx.Token == "" {
			output.Warning("Not logged in")
			return nil
		}

		// Clear token
		ctx.Token = ""

		// Save configuration
		configPath := viper.ConfigFileUsed()
		if configPath == "" {
			home, _ := os.UserHomeDir()
			configPath = filepath.Join(home, ".docker-swarm-ctl", "config.yaml")
		}
		
		if err := cfg.Save(configPath); err != nil {
			return fmt.Errorf("failed to save config: %w", err)
		}

		output.Success("Successfully logged out from %s", cfg.CurrentContext)
		return nil
	},
}

var whoamiCmd = &cobra.Command{
	Use:   "whoami",
	Short: "Display the current user",
	Long:  `Show information about the currently authenticated user`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if cfg.CurrentContext == "" {
			return fmt.Errorf("not logged in")
		}

		ctx, ok := cfg.Contexts[cfg.CurrentContext]
		if !ok || ctx.Username == "" {
			return fmt.Errorf("not logged in")
		}

		fmt.Printf("Current user: %s\n", ctx.Username)
		fmt.Printf("Context: %s (%s)\n", cfg.CurrentContext, ctx.APIUrl)
		fmt.Printf("Authenticated: %s\n", output.FormatBool(ctx.Token != ""))

		return nil
	},
}

func init() {
	authCmd.AddCommand(loginCmd)
	authCmd.AddCommand(logoutCmd)
	authCmd.AddCommand(whoamiCmd)

	loginCmd.Flags().StringP("username", "u", "", "Username")
	loginCmd.Flags().StringP("password", "p", "", "Password (will prompt if not provided)")
}