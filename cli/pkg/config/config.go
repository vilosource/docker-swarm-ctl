package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Context represents a configuration context
type Context struct {
	APIUrl    string `yaml:"api_url"`
	Username  string `yaml:"username,omitempty"`
	Token     string `yaml:"token,omitempty"`
	VerifySSL bool   `yaml:"verify_ssl"`
}

// Config represents the CLI configuration
type Config struct {
	Contexts       map[string]*Context `yaml:"contexts"`
	CurrentContext string              `yaml:"current_context,omitempty"`
}

// New creates a new Config instance
func New() *Config {
	return &Config{
		Contexts: make(map[string]*Context),
	}
}

// Save saves the configuration to file
func (c *Config) Save(path string) error {
	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	// Ensure directory exists
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	// Write file
	if err := os.WriteFile(path, data, 0600); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}

// Load loads configuration from file
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// Return empty config if file doesn't exist
			return New(), nil
		}
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	// Initialize contexts map if nil
	if cfg.Contexts == nil {
		cfg.Contexts = make(map[string]*Context)
	}

	return &cfg, nil
}

// AddContext adds or updates a context
func (c *Config) AddContext(name string, ctx *Context) {
	c.Contexts[name] = ctx
	
	// Set as current if it's the first context
	if c.CurrentContext == "" {
		c.CurrentContext = name
	}
}

// RemoveContext removes a context
func (c *Config) RemoveContext(name string) {
	delete(c.Contexts, name)
	
	// Update current context if needed
	if c.CurrentContext == name {
		c.CurrentContext = ""
		// Set first available context as current
		for k := range c.Contexts {
			c.CurrentContext = k
			break
		}
	}
}

// GetCurrentContext returns the current context
func (c *Config) GetCurrentContext() (*Context, error) {
	if c.CurrentContext == "" {
		return nil, fmt.Errorf("no current context set")
	}
	
	ctx, ok := c.Contexts[c.CurrentContext]
	if !ok {
		return nil, fmt.Errorf("context '%s' not found", c.CurrentContext)
	}
	
	return ctx, nil
}

// UseContext switches to a different context
func (c *Config) UseContext(name string) error {
	if _, ok := c.Contexts[name]; !ok {
		return fmt.Errorf("context '%s' not found", name)
	}
	
	c.CurrentContext = name
	return nil
}