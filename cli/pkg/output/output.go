package output

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/olekukonko/tablewriter"
	"gopkg.in/yaml.v3"
)

// Printer interface for different output formats
type Printer interface {
	Print(data interface{}) error
}

// NewPrinter creates a printer based on the format
func NewPrinter(format string) Printer {
	switch strings.ToLower(format) {
	case "json":
		return &JSONPrinter{}
	case "yaml":
		return &YAMLPrinter{}
	case "wide":
		return &TablePrinter{Wide: true}
	default:
		return &TablePrinter{Wide: false}
	}
}

// JSONPrinter outputs data as JSON
type JSONPrinter struct{}

func (p *JSONPrinter) Print(data interface{}) error {
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(data)
}

// YAMLPrinter outputs data as YAML
type YAMLPrinter struct{}

func (p *YAMLPrinter) Print(data interface{}) error {
	return yaml.NewEncoder(os.Stdout).Encode(data)
}

// TablePrinter outputs data as a table
type TablePrinter struct {
	Wide bool
}

func (p *TablePrinter) Print(data interface{}) error {
	// This is a simplified implementation
	// In a real implementation, we'd use reflection or type switches
	// to handle different data types appropriately
	fmt.Printf("%+v\n", data)
	return nil
}

// PrintTable prints data in table format
func PrintTable(headers []string, rows [][]string) {
	table := tablewriter.NewWriter(os.Stdout)
	table.SetHeader(headers)
	table.SetBorder(false)
	table.SetHeaderLine(false)
	table.SetColumnSeparator("")
	table.SetHeaderAlignment(tablewriter.ALIGN_LEFT)
	table.SetAlignment(tablewriter.ALIGN_LEFT)
	
	for _, row := range rows {
		table.Append(row)
	}
	
	table.Render()
}

// Success prints a success message
func Success(format string, args ...interface{}) {
	color.Green("✓ " + fmt.Sprintf(format, args...))
}

// Error prints an error message
func Error(format string, args ...interface{}) {
	color.Red("✗ " + fmt.Sprintf(format, args...))
}

// Warning prints a warning message
func Warning(format string, args ...interface{}) {
	color.Yellow("⚠ " + fmt.Sprintf(format, args...))
}

// Info prints an info message
func Info(format string, args ...interface{}) {
	color.Blue("ℹ " + fmt.Sprintf(format, args...))
}

// FormatTimestamp formats a timestamp to a human-readable format
func FormatTimestamp(t time.Time) string {
	if t.IsZero() {
		return "-"
	}
	
	now := time.Now()
	diff := now.Sub(t)
	
	switch {
	case diff < time.Minute:
		return "just now"
	case diff < time.Hour:
		return fmt.Sprintf("%dm ago", int(diff.Minutes()))
	case diff < 24*time.Hour:
		return fmt.Sprintf("%dh ago", int(diff.Hours()))
	default:
		return fmt.Sprintf("%dd ago", int(diff.Hours()/24))
	}
}

// TruncateID truncates an ID to a shorter length
func TruncateID(id string, length int) string {
	if len(id) <= length {
		return id
	}
	return id[:length]
}

// FormatBool formats a boolean as a checkmark or X
func FormatBool(b bool) string {
	if b {
		return color.GreenString("✓")
	}
	return color.RedString("✗")
}