# cert4k8s

cert4k8s is a utility created using the Python Kubernetes library to address the limitation in cert-manager tool's native support for Istio Gateway objects. Unlike Ingress objects, cert-manager does not automatically create TLS certificates based on host specifications in Istio Gateway objects. To overcome this limitation, cert4k8s was developed.


## Purpose

The primary purpose of cert4k8s is to facilitate the creation of cert-manager certificate objects for Istio Gateway, ensuring seamless TLS certificate management. The utility monitors Istio Gateway objects and takes action based on specific annotations.


## Usage

### Docker Image

The Docker image for cert4k8s is hosted at:

```bash
ghcr.io/jotheesh-joe/cert4k8s:0.0.1
```


### Project Structure

- code/

  - Dockerfile: Dockerfile for building the cert4k8s Docker image.
  - app.py: Python script implementing the cert4k8s utility.
  - requirements: Dependencies required for running cert4k8s.


- helm/

  - Helm chart for deploying and configuring cert4k8s within a Kubernetes cluster.
 

### Functionality

cert4k8s monitors Istio Gateway objects and performs the following actions:

- If a new Istio Gateway is created with the annotations:
  - jotheesh-joe.biz/cert4k8s=enabled
  - jotheesh-joe.biz/cert4k8s-type=dedicated
  cert4k8s will create a cert-manager certificate object, leading to the creation of a Kubernetes secret with TLS certificates.

- if an existing Istio Gateway is modified or deleted with the specified annotations, cert4k8s will respond accordingly.


### Usage Example

To deploy cert4k8s using the Helm chart, follow these steps:

```bash
helm install cert4k8s ./helm/cert4k8s
```


### Configuration

Ensure that the Istio Gateway objects include the following annotations for cert4k8s to take action:

 - jotheesh-joe.biz/cert4k8s=enabled
 - jotheesh-joe.biz/cert4k8s-type=dedicated


## Issues and Support
If you encounter any issues or need support, please create an [issue](https://github.com/Jotheesh-Joe/cert4k8s/issues)





