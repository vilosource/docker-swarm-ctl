package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"github.com/docker-swarm-ctl/cli/pkg/output"
)

var getCmd = &cobra.Command{
	Use:   "get TYPE [NAME]",
	Short: "Display one or many resources",
	Long: `Display one or many resources.

Resource types:
  - hosts, host
  - nodes, node
  - services, service, svc
  - secrets, secret
  - configs, config
  - containers, container

Examples:
  # List all hosts
  docker-swarm-ctl get hosts

  # Get a specific service
  docker-swarm-ctl get service nginx --host <host-id>

  # List nodes with JSON output
  docker-swarm-ctl get nodes --host <host-id> -o json`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		resourceType := strings.ToLower(args[0])
		var resourceName string
		if len(args) > 1 {
			resourceName = args[1]
		}

		switch resourceType {
		case "hosts", "host":
			return getHosts(cmd, resourceName)
		case "nodes", "node":
			return getNodes(cmd, resourceName)
		case "services", "service", "svc":
			return getServices(cmd, resourceName)
		case "secrets", "secret":
			return getSecrets(cmd, resourceName)
		case "configs", "config":
			return getConfigs(cmd, resourceName)
		case "containers", "container":
			return getContainers(cmd, resourceName)
		default:
			return fmt.Errorf("unknown resource type: %s", resourceType)
		}
	},
}

func getHosts(cmd *cobra.Command, name string) error {
	if err := requireAuth(); err != nil {
		return err
	}

	if name != "" {
		// Get specific host
		host, err := apiClient.GetHost(name)
		if err != nil {
			return err
		}

		printer := output.NewPrinter(outputFormat)
		return printer.Print(host)
	}

	// List all hosts
	hosts, err := apiClient.ListHosts()
	if err != nil {
		return err
	}

	if outputFormat == "json" || outputFormat == "yaml" {
		printer := output.NewPrinter(outputFormat)
		return printer.Print(hosts)
	}

	// Table output
	headers := []string{"ID", "NAME", "URL", "ACTIVE", "CREATED"}
	var rows [][]string

	for _, host := range hosts {
		rows = append(rows, []string{
			output.TruncateID(host.ID, 12),
			host.DisplayName,
			host.URL,
			output.FormatBool(host.IsActive),
			output.FormatTimestamp(host.CreatedAt),
		})
	}

	output.PrintTable(headers, rows)
	return nil
}

func getNodes(cmd *cobra.Command, name string) error {
	hostID, err := requireHost(cmd)
	if err != nil {
		return err
	}

	if err := requireAuth(); err != nil {
		return err
	}

	nodes, err := apiClient.ListNodes(hostID)
	if err != nil {
		return err
	}

	if outputFormat == "json" || outputFormat == "yaml" {
		printer := output.NewPrinter(outputFormat)
		return printer.Print(nodes)
	}

	// Table output
	headers := []string{"ID", "HOSTNAME", "STATUS", "AVAILABILITY", "MANAGER STATUS", "ENGINE VERSION"}
	var rows [][]string

	for _, node := range nodes {
		managerStatus := node.ManagerStatus
		if managerStatus == "" {
			managerStatus = "-"
		}

		rows = append(rows, []string{
			output.TruncateID(node.ID, 12),
			node.Hostname,
			node.Status,
			node.Availability,
			managerStatus,
			node.EngineVersion,
		})
	}

	output.PrintTable(headers, rows)
	return nil
}

func getServices(cmd *cobra.Command, name string) error {
	hostID, err := requireHost(cmd)
	if err != nil {
		return err
	}

	if err := requireAuth(); err != nil {
		return err
	}

	services, err := apiClient.ListServices(hostID)
	if err != nil {
		return err
	}

	if outputFormat == "json" || outputFormat == "yaml" {
		printer := output.NewPrinter(outputFormat)
		return printer.Print(services)
	}

	// Table output
	headers := []string{"ID", "NAME", "MODE", "REPLICAS", "IMAGE"}
	var rows [][]string

	for _, service := range services {
		replicas := fmt.Sprintf("%d", service.Replicas)
		if service.Mode != "replicated" {
			replicas = service.Mode
		}

		rows = append(rows, []string{
			output.TruncateID(service.ID, 12),
			service.Name,
			service.Mode,
			replicas,
			service.Image,
		})
	}

	output.PrintTable(headers, rows)
	return nil
}

func getSecrets(cmd *cobra.Command, name string) error {
	hostID, err := requireHost(cmd)
	if err != nil {
		return err
	}

	if err := requireAuth(); err != nil {
		return err
	}

	// TODO: Implement secrets listing
	output.Info("Listing secrets on host %s", hostID)
	return nil
}

func getConfigs(cmd *cobra.Command, name string) error {
	hostID, err := requireHost(cmd)
	if err != nil {
		return err
	}

	if err := requireAuth(); err != nil {
		return err
	}

	// TODO: Implement configs listing
	output.Info("Listing configs on host %s", hostID)
	return nil
}

func getContainers(cmd *cobra.Command, name string) error {
	hostID, err := requireHost(cmd)
	if err != nil {
		return err
	}

	if err := requireAuth(); err != nil {
		return err
	}

	// TODO: Implement containers listing
	output.Info("Listing containers on host %s", hostID)
	return nil
}

func init() {
	getCmd.Flags().String("host", "", "Host ID (required for swarm resources)")
	getCmd.Flags().StringP("selector", "l", "", "Selector (label query)")
	getCmd.Flags().StringP("filter", "f", "", "Filter output")
	getCmd.Flags().BoolP("watch", "w", false, "Watch for changes")
	getCmd.Flags().BoolP("all-hosts", "A", false, "List resources from all hosts")
}