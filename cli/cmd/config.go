package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/docker-swarm-ctl/cli/pkg/config"
	"github.com/docker-swarm-ctl/cli/pkg/output"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage CLI configuration",
	Long:  `Manage contexts and other CLI configuration settings`,
}

var configViewCmd = &cobra.Command{
	Use:   "view",
	Short: "View current configuration",
	Long:  `Display all configured contexts and settings`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(cfg.Contexts) == 0 {
			output.Warning("No contexts configured")
			return nil
		}

		headers := []string{"CURRENT", "NAME", "API URL", "USER", "AUTH"}
		var rows [][]string

		for name, ctx := range cfg.Contexts {
			current := ""
			if name == cfg.CurrentContext {
				current = "*"
			}
			
			user := ctx.Username
			if user == "" {
				user = "-"
			}
			
			auth := "No"
			if ctx.Token != "" {
				auth = "Yes"
			}

			rows = append(rows, []string{
				current,
				name,
				ctx.APIUrl,
				user,
				auth,
			})
		}

		output.PrintTable(headers, rows)
		return nil
	},
}

var configAddContextCmd = &cobra.Command{
	Use:   "add-context NAME",
	Short: "Add a new context",
	Long:  `Add a new context configuration`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]
		apiURL, _ := cmd.Flags().GetString("api-url")
		username, _ := cmd.Flags().GetString("username")
		verifySSL, _ := cmd.Flags().GetBool("verify-ssl")

		if apiURL == "" {
			return fmt.Errorf("--api-url is required")
		}

		// Add context
		cfg.AddContext(name, &config.Context{
			APIUrl:    apiURL,
			Username:  username,
			VerifySSL: verifySSL,
		})

		// Save configuration
		configPath := viper.ConfigFileUsed()
		if configPath == "" {
			home, _ := os.UserHomeDir()
			configPath = filepath.Join(home, ".docker-swarm-ctl", "config.yaml")
		}
		
		if err := cfg.Save(configPath); err != nil {
			return fmt.Errorf("failed to save config: %w", err)
		}

		output.Success("Context '%s' added successfully", name)
		
		if cfg.CurrentContext == name {
			output.Info("Switched to context '%s'", name)
		}

		return nil
	},
}

var configRemoveContextCmd = &cobra.Command{
	Use:   "remove-context NAME",
	Short: "Remove a context",
	Long:  `Remove a context configuration`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		if _, ok := cfg.Contexts[name]; !ok {
			return fmt.Errorf("context '%s' not found", name)
		}

		// Confirm if it's the current context
		if cfg.CurrentContext == name {
			fmt.Printf("'%s' is the current context. Remove anyway? (y/N): ", name)
			var response string
			fmt.Scanln(&response)
			if response != "y" && response != "Y" {
				output.Info("Removal cancelled")
				return nil
			}
		}

		cfg.RemoveContext(name)

		// Save configuration
		configPath := viper.ConfigFileUsed()
		if configPath == "" {
			home, _ := os.UserHomeDir()
			configPath = filepath.Join(home, ".docker-swarm-ctl", "config.yaml")
		}
		
		if err := cfg.Save(configPath); err != nil {
			return fmt.Errorf("failed to save config: %w", err)
		}

		output.Success("Context '%s' removed", name)
		return nil
	},
}

var configUseContextCmd = &cobra.Command{
	Use:   "use-context NAME",
	Short: "Switch to a different context",
	Long:  `Set the current context`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		name := args[0]

		if err := cfg.UseContext(name); err != nil {
			// Show available contexts
			output.Error("Context '%s' not found", name)
			output.Info("Available contexts:")
			for ctxName := range cfg.Contexts {
				fmt.Printf("  - %s\n", ctxName)
			}
			return err
		}

		// Save configuration
		configPath := viper.ConfigFileUsed()
		if configPath == "" {
			home, _ := os.UserHomeDir()
			configPath = filepath.Join(home, ".docker-swarm-ctl", "config.yaml")
		}
		
		if err := cfg.Save(configPath); err != nil {
			return fmt.Errorf("failed to save config: %w", err)
		}

		output.Success("Switched to context '%s'", name)
		return nil
	},
}

var configCurrentContextCmd = &cobra.Command{
	Use:   "current-context",
	Short: "Display the current context",
	Long:  `Show details about the current context`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if cfg.CurrentContext == "" {
			output.Warning("No current context set")
			return nil
		}

		ctx, ok := cfg.Contexts[cfg.CurrentContext]
		if !ok {
			return fmt.Errorf("current context '%s' not found in config", cfg.CurrentContext)
		}

		fmt.Printf("Current context: %s\n", cfg.CurrentContext)
		fmt.Printf("API URL: %s\n", ctx.APIUrl)
		fmt.Printf("Username: %s\n", func() string {
			if ctx.Username != "" {
				return ctx.Username
			}
			return "-"
		}())
		fmt.Printf("Authenticated: %s\n", output.FormatBool(ctx.Token != ""))
		fmt.Printf("Verify SSL: %s\n", output.FormatBool(ctx.VerifySSL))

		return nil
	},
}

func init() {
	configCmd.AddCommand(configViewCmd)
	configCmd.AddCommand(configAddContextCmd)
	configCmd.AddCommand(configRemoveContextCmd)
	configCmd.AddCommand(configUseContextCmd)
	configCmd.AddCommand(configCurrentContextCmd)

	configAddContextCmd.Flags().String("api-url", "", "API URL for the context")
	configAddContextCmd.Flags().String("username", "", "Default username for this context")
	configAddContextCmd.Flags().Bool("verify-ssl", true, "Verify SSL certificates")
	configAddContextCmd.MarkFlagRequired("api-url")
}