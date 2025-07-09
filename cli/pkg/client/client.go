package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Client represents the API client
type Client struct {
	BaseURL    string
	Token      string
	HTTPClient *http.Client
}

// New creates a new API client
func New(baseURL, token string) *Client {
	return &Client{
		BaseURL: strings.TrimRight(baseURL, "/"),
		Token:   token,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// request performs an HTTP request
func (c *Client) request(method, endpoint string, body interface{}, params map[string]string) (*http.Response, error) {
	// Build URL
	u, err := url.Parse(c.BaseURL + "/" + strings.TrimLeft(endpoint, "/"))
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	// Add query parameters
	if params != nil {
		q := u.Query()
		for k, v := range params {
			q.Set(k, v)
		}
		u.RawQuery = q.Encode()
	}

	// Prepare body
	var bodyReader io.Reader
	if body != nil {
		jsonData, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(jsonData)
	}

	// Create request
	req, err := http.NewRequest(method, u.String(), bodyReader)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.Token != "" {
		req.Header.Set("Authorization", "Bearer "+c.Token)
	}

	// Execute request
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	return resp, nil
}

// doRequest performs a request and handles the response
func (c *Client) doRequest(method, endpoint string, body interface{}, params map[string]string, result interface{}) error {
	resp, err := c.request(method, endpoint, body, params)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Read response body
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	// Check status code
	if resp.StatusCode >= 400 {
		var errorResp struct {
			Detail string `json:"detail"`
		}
		if err := json.Unmarshal(respBody, &errorResp); err == nil && errorResp.Detail != "" {
			return fmt.Errorf("API error (%d): %s", resp.StatusCode, errorResp.Detail)
		}
		return fmt.Errorf("API error (%d): %s", resp.StatusCode, string(respBody))
	}

	// Parse response if needed
	if result != nil && len(respBody) > 0 {
		if err := json.Unmarshal(respBody, result); err != nil {
			return fmt.Errorf("failed to parse response: %w", err)
		}
	}

	return nil
}

// GET performs a GET request
func (c *Client) GET(endpoint string, params map[string]string, result interface{}) error {
	return c.doRequest("GET", endpoint, nil, params, result)
}

// POST performs a POST request
func (c *Client) POST(endpoint string, body interface{}, params map[string]string, result interface{}) error {
	return c.doRequest("POST", endpoint, body, params, result)
}

// PUT performs a PUT request
func (c *Client) PUT(endpoint string, body interface{}, params map[string]string, result interface{}) error {
	return c.doRequest("PUT", endpoint, body, params, result)
}

// DELETE performs a DELETE request
func (c *Client) DELETE(endpoint string, params map[string]string, result interface{}) error {
	return c.doRequest("DELETE", endpoint, nil, params, result)
}

// Login authenticates and stores the token
func (c *Client) Login(username, password string) error {
	// Create form data
	form := url.Values{}
	form.Add("username", username)
	form.Add("password", password)

	// Create request
	req, err := http.NewRequest("POST", c.BaseURL+"/auth/login", strings.NewReader(form.Encode()))
	if err != nil {
		return fmt.Errorf("failed to create login request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	// Execute request
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("login request failed: %w", err)
	}
	defer resp.Body.Close()

	// Read response
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read login response: %w", err)
	}

	// Check status
	if resp.StatusCode != 200 {
		return fmt.Errorf("login failed (%d): %s", resp.StatusCode, string(respBody))
	}

	// Parse response
	var loginResp struct {
		AccessToken string `json:"access_token"`
	}
	if err := json.Unmarshal(respBody, &loginResp); err != nil {
		return fmt.Errorf("failed to parse login response: %w", err)
	}

	// Store token
	c.Token = loginResp.AccessToken
	return nil
}

// Host operations
type Host struct {
	ID          string    `json:"id"`
	DisplayName string    `json:"display_name"`
	URL         string    `json:"url"`
	IsActive    bool      `json:"is_active"`
	TLSEnabled  bool      `json:"tls_enabled"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type HostList struct {
	Items []Host `json:"items"`
	Total int    `json:"total"`
}

func (c *Client) ListHosts() ([]Host, error) {
	var result HostList
	if err := c.GET("/hosts/", nil, &result); err != nil {
		return nil, err
	}
	return result.Items, nil
}

func (c *Client) GetHost(hostID string) (*Host, error) {
	var result Host
	if err := c.GET("/hosts/"+hostID, nil, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// Swarm operations
type SwarmInfo struct {
	ID        string    `json:"ID"`
	CreatedAt time.Time `json:"CreatedAt"`
	UpdatedAt time.Time `json:"UpdatedAt"`
	Spec      struct {
		Orchestration map[string]interface{} `json:"Orchestration"`
		Raft          map[string]interface{} `json:"Raft"`
		Dispatcher    map[string]interface{} `json:"Dispatcher"`
		CAConfig      map[string]interface{} `json:"CAConfig"`
	} `json:"Spec"`
}

func (c *Client) GetSwarmInfo(hostID string) (*SwarmInfo, error) {
	var result SwarmInfo
	params := map[string]string{"host_id": hostID}
	if err := c.GET("/swarm/", params, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// Node operations
type Node struct {
	ID             string `json:"id"`
	Hostname       string `json:"hostname"`
	Status         string `json:"status"`
	Availability   string `json:"availability"`
	Role           string `json:"role"`
	ManagerStatus  string `json:"manager_status,omitempty"`
	EngineVersion  string `json:"engine_version"`
}

type NodeList struct {
	Nodes []Node `json:"nodes"`
	Total int    `json:"total"`
}

func (c *Client) ListNodes(hostID string) ([]Node, error) {
	var result NodeList
	params := map[string]string{"host_id": hostID}
	if err := c.GET("/nodes", params, &result); err != nil {
		return nil, err
	}
	return result.Nodes, nil
}

// Service operations
type Service struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Image    string `json:"image"`
	Replicas int    `json:"replicas"`
	Mode     string `json:"mode"`
}

type ServiceList struct {
	Services []Service `json:"services"`
	Total    int       `json:"total"`
}

func (c *Client) ListServices(hostID string) ([]Service, error) {
	var result ServiceList
	params := map[string]string{"host_id": hostID}
	if err := c.GET("/services", params, &result); err != nil {
		return nil, err
	}
	return result.Services, nil
}