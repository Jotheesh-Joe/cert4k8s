# cert4k8s
cert4k8s is a utility created using the Python Kubernetes library to address the limitation in cert-manager tool's native support for Istio Gateway objects. Unlike Ingress objects, cert-manager does not automatically create TLS certificates based on host specifications in Istio Gateway objects. To overcome this limitation, cert4k8s was developed.
