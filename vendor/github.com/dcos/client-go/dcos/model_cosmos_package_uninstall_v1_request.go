/*
 * DC/OS
 *
 * DC/OS API
 *
 * API version: 1.0.0
 */

// Code generated by OpenAPI Generator (https://openapi-generator.tech); DO NOT EDIT.

package dcos

type CosmosPackageUninstallV1Request struct {
	AppId       string `json:"appId,omitempty"`
	PackageName string `json:"packageName"`
	All         bool   `json:"all,omitempty"`
}
