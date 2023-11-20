from kubernetes import client, config, watch
from urllib3 import exceptions
import datetime
import time
import sys
import os

# Configs can be set in Configuration class directly or using helper utility
config.incluster_config.load_incluster_config()

v1 = client.CustomObjectsApi()
w = watch.Watch()



url_str1 = os.environ["URLS"]
url_str2 = url_str1.replace(' ', '')
url_list = url_str2.split(',')
url_tuple = tuple(url_list)
print(url_tuple)


def list_cert_details():
    try:
        res = v1.list_namespaced_custom_object(group="cert-manager.io", version="v1", plural="certificates",
                                               namespace="istio-system")
        dnsnames_arr = []

        certnames_arr = []

        for item in res['items']:
            certnames_arr.append(item['metadata']['name'])
            for dns_name in item['spec']['dnsNames']:
                dnsnames_arr.append(dns_name)

        cert_dict = {
            'cert_names': certnames_arr,
            'dns_names': dnsnames_arr
        }
        return cert_dict
    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime(
            "%Y-%m-%d %H:%M:%S") + ': ' + "Could not list the certificates in istio-system namespace : " + "error message - " + str(e))


def create_wild_card_cert(urls):
    for url in urls:
        url_name = url.replace(".", "-")
        url_arr = url.split(".")
        secret_name = url_arr[0] + '-' + url_arr[1] + '-wildcard-cert'
        dns_name = '*.' + url
        cert_list = list_cert_details()
        if url_name not in cert_list['cert_names'] and dns_name not in cert_list['dns_names']:
            body = {}
            body['apiVersion'] = 'cert-manager.io/v1'
            body['kind'] = 'Certificate'
            body['metadata'] = {}
            body['metadata']['name'] = url_name
            body['metadata']['namespace'] = "istio-system"
            body['metadata']['labels'] = {}
            body['metadata']['labels']['created-by'] = 'cert4k8s'
            body['spec'] = {}
            body['spec']['dnsNames'] = [dns_name]
            body['spec']['issuerRef'] = {}
            body['spec']['issuerRef']['group'] = 'cert-manager.io'
            body['spec']['issuerRef']['kind'] = 'ClusterIssuer'
            body['spec']['issuerRef']['name'] = 'letsencrypt-dns01'
            body['spec']['secretName'] = secret_name
            body['spec']['usages'] = ['digital signature', 'key encipherment']
            try:
                now = datetime.datetime.now()
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'trying to create a cert')
                time.sleep(10)
                res = v1.create_namespaced_custom_object(group="cert-manager.io", version="v1", plural="certificates",
                                                         namespace="istio-system", body=body)
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(res))
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'wild card certificate created')
            except Exception as e:
                now = datetime.datetime.now()
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "Could not create new certificate: " + "error message - " + str(e))
        else:
            now = datetime.datetime.now()
            print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'The wildcard certificate or dns is already in use, so no action will be taken')
            print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'If new wildcard certificate is needed, delete the existing wildcard certificate and secret')


def list_gw(namespace):
    try:
        now = datetime.datetime.now()
        res_gw = v1.list_namespaced_custom_object(group="networking.istio.io", version="v1beta1", plural="gateways",
                                                  namespace=namespace)
        gw_list = []
        for item in res_gw['items']:
            gw_name = item['metadata']['name']
            gw_list.append(gw_name)
        return gw_list
    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime(
            "%Y-%m-%d %H:%M:%S") + ': ' + "Could not list gateways in the namespace : " + "error message - " + str(e))


def create_cert(event, count):
    body = {}
    body['apiVersion'] = 'cert-manager.io/v1'
    body['kind'] = 'Certificate'
    body['metadata'] = {}
    body['metadata']['name'] = event['Name'] + '-' + event['Namespace'] + '-' + 'cert''-' + str(count)
    body['metadata']['namespace'] = "istio-system"
    body['metadata']['labels'] = {}
    body['metadata']['labels']['created-by'] = 'cert4k8s'
    body['spec'] = {}
    body['spec']['dnsNames'] = event['hostnames']
    body['spec']['issuerRef'] = {}
    body['spec']['issuerRef']['group'] = 'cert-manager.io'
    body['spec']['issuerRef']['kind'] = 'ClusterIssuer'
    body['spec']['issuerRef']['name'] = 'letsencrypt-dns01'
    body['spec']['secretName'] = event['secret_name']
    body['spec']['usages'] = ['digital signature', 'key encipherment']
    try:
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'trying to create a cert')
        time.sleep(120)
        res = v1.create_namespaced_custom_object(group="cert-manager.io", version="v1", plural="certificates",
                                                 namespace="istio-system", body=body)
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(res))
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'certificate created')
    except Exception as e:
        now = datetime.datetime.now()
        print(
            now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "Could not create new certificate: " + "error message - " + str(
                e))


def patch_cert(event, count):
    cert_name = event['Name'] + '-' + event['Namespace'] + '-' + 'cert''-' + str(count)
    body = {}
    body['apiVersion'] = 'cert-manager.io/v1'
    body['kind'] = 'Certificate'
    body['metadata'] = {}
    body['metadata']['name'] = cert_name
    body['metadata']['namespace'] = "istio-system"
    body['metadata']['labels'] = {}
    body['metadata']['labels']['created-by'] = 'cert4k8s'
    body['spec'] = {}
    body['spec']['dnsNames'] = event['hostnames']
    body['spec']['issuerRef'] = {}
    body['spec']['issuerRef']['group'] = 'cert-manager.io'
    body['spec']['issuerRef']['kind'] = 'ClusterIssuer'
    body['spec']['issuerRef']['name'] = 'letsencrypt-dns01'
    body['spec']['secretName'] = event['secret_name']
    body['spec']['usages'] = ['digital signature', 'key encipherment']
    try:
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'trying to patch a cert')
        time.sleep(90)
        res = v1.patch_namespaced_custom_object(group="cert-manager.io", version="v1", plural="certificates",
                                                namespace="istio-system", name=cert_name,
                                                body=body)
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(res))
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'certificate patched')
    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "Could not patch the certificate: " + "error message - " + str(
            e))


def get_cert_detail(name):
    try:
        now = datetime.datetime.now()
        res_cert = v1.get_namespaced_custom_object(group="cert-manager.io", version="v1", namespace="istio-system",
                                                   plural="certificates", name=name)
        cert_dict = {
            'hostnames': res_cert['spec']['dnsNames'],
            'secret_name': res_cert['spec']['secretName']
        }
        return cert_dict
    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime(
            "%Y-%m-%d %H:%M:%S") + ': ' + "Could not find the certificate for the gateway server: " + "error message - " + str(
            e))


def event_added(each_event, count):
    try:
        now = datetime.datetime.now()
        resp = list_cert_details()
        new_dns_list = []
        cert_names = resp['cert_names']
        dns_names = resp['dns_names']
        if each_event['Name'] + '-' + each_event['Namespace'] + '-' + 'cert' + '-' + str(count) in cert_names:
            print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "certificate already present for the gateway")
        else:
            for hostname in each_event['hostnames']:
                if hostname in dns_names:
                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "hostname already present in a certificate")
                else:
                    new_dns_list.append(hostname)

        if len(new_dns_list) > 0:
            each_event['hostnames'] = new_dns_list
            create_cert(each_event, count)
    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime(
            "%Y-%m-%d %H:%M:%S") + ': ' + "issue in creating a new certificate: " + "error message - " + str(e))


def event_modified(each_event):
    try:
        now = datetime.datetime.now()
        for count, value in enumerate(each_event['servers']):
            cert_name = each_event['Name'] + '-' + each_event['Namespace'] + '-' + 'cert' + '-' + str(count + 1)
            cert_details = get_cert_detail(cert_name)
            if value == cert_details:
                print(now.strftime(
                    "%Y-%m-%d %H:%M:%S") + ': ' + "no modification to dns and secret so patching is not needed")
            else:
                event_dict = {
                    'Name': each_event['Name'],
                    'Namespace': each_event['Namespace'],
                    'hostnames': value['hostnames'],
                    'secret_name': value['secret_name']
                }
                patch_cert(event_dict, count + 1)

    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime(
            "%Y-%m-%d %H:%M:%S") + ': ' + "Modified Gateway could not be found: " + "error message - " + str(e))


def event_deleted(each_event):
    try:
        now = datetime.datetime.now()
        for count, value in enumerate(each_event['servers']):
            cert_name = each_event['Name'] + '-' + each_event['Namespace'] + '-' + 'cert' + '-' + str(count + 1)
            try:
                resp = v1.delete_namespaced_custom_object(group="cert-manager.io", version="v1", plural="certificates",
                                                          namespace="istio-system", name=cert_name)
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(resp))
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'certificate deleted successfully')
            except Exception as e:
                print(now.strftime(
                    "%Y-%m-%d %H:%M:%S") + ': ' + "could not delete the certificate: " + "error message - " + str(e))
    except Exception as e:
        now = datetime.datetime.now()
        print(
            now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + "Error in event delete function: " + "error message - " + str(e))


def main():
    try:
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'Starting cert4k8s')
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'Successfully started cert4k8s')
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'checking for istio gateways in the cluster')
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'The following domains are supported by cert4k8s in this cluster are : ' + str(url_tuple))
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'Trying to create wildcard certificate')
        create_wild_card_cert(url_tuple)
        resource_version = None
        cycle = 0
        while True:
            try:
                if cycle < 365:
                    cycle += 1
                    print('cycle - ' + str(cycle))
                    print('watching for new gateway resource...')
                    for event in w.stream(func=v1.list_cluster_custom_object, group="networking.istio.io",
                                          version="v1beta1",
                                          plural="gateways", resource_version=resource_version, timeout_seconds=240):
                        try:
                            resource_version = event['object']['metadata']['resourceVersion']
                            now = datetime.datetime.now()
                            # checking for correct annotation
                            annotation_dict = event['object']['metadata']['annotations']
                            if ('bakery.volvocars.biz/cert4k8s', 'enabled') in annotation_dict.items() and ('bakery.volvocars.biz/cert4k8s-type', 'dedicated') in annotation_dict.items():
                                newEvent = {
                                    "Event": event['type'],
                                    'Name': event['object']['metadata']['name'],
                                    'Namespace': event['object']['metadata']['namespace']
                                }
                                if newEvent['Event'] == 'ADDED':
                                    fullEvent_arr = []
                                    host_arr = []
                                    for server in event['object']['spec']['servers']:
                                        if server['port']['protocol'] == 'HTTPS' or server['port']['protocol'] == 'TLS':
                                            for hostname in server['hosts']:
                                                if hostname.endswith(url_tuple):
                                                    host_arr.append(hostname)
                                                else:
                                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(hostname) + ' the domain is not supported')
                                            host_dict = {
                                                'hostnames': host_arr,
                                                'secret_name': server['tls']['credentialName']
                                            }

                                            fullEvent = newEvent | host_dict
                                            fullEvent_arr.append(fullEvent)

                                    else:
                                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': The Protocol mentioned in the Gateway is not supported')

                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(fullEvent_arr))

                                    if len(host_arr) > 0:
                                        for count, each_event in enumerate(fullEvent_arr):
                                            event_added(each_event, count + 1)
                                    else:
                                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(fullEvent_arr) + 'contains a domain which is not supported or the protocol is not supported')

                                    #w.stop()

                                elif newEvent['Event'] == 'DELETED':

                                    server_arr_del = []
                                    host_arr_d = []
                                    for server in event['object']['spec']['servers']:
                                        if server['port']['protocol'] == 'HTTPS' or server['port']['protocol'] == 'TLS':
                                            for hostname in server['hosts']:
                                                if hostname.endswith(url_tuple):
                                                    host_arr_d.append(hostname)
                                                else:
                                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                        hostname) + ' the domain is not supported')
                                            host_dict_m = {
                                                'hostnames': host_arr_d,
                                                'secret_name': server['tls']['credentialName']
                                            }
                                            server_arr_del.append(host_dict_m)

                                    server_dict = {
                                        'servers': server_arr_del
                                    }
                                    fullEvent_dict_del = newEvent | server_dict

                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(fullEvent_dict_del))
                                    if len(host_arr_d) > 0:
                                        event_deleted(fullEvent_dict_del)
                                    else:
                                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                        fullEvent_dict_del) + 'contains a domain which is not supported')
                                    #w.stop()

                                elif newEvent['Event'] == 'MODIFIED':
                                    gwlist = list_gw(newEvent['Namespace'])
                                    host_arr_m1 = []
                                    server_arr = []
                                    for server in event['object']['spec']['servers']:
                                        if server['port']['protocol'] == 'HTTPS' or server['port']['protocol'] == 'TLS':
                                            for hostname in server['hosts']:
                                                if hostname.endswith(url_tuple):
                                                    host_arr_m1.append(hostname)
                                                else:
                                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                        hostname) + ' the domain is not supported')
                                            host_dict_m = {
                                                'hostnames': host_arr_m1,
                                                'secret_name': server['tls']['credentialName']
                                            }
                                            server_arr.append(host_dict_m)
                                    server_dict = {
                                        'servers': server_arr
                                    }
                                    fullEvent_dict = newEvent | server_dict

                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(fullEvent_dict))
                                    if newEvent['Name'] not in gwlist:
                                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + newEvent[
                                            "Name"] + '- gateway is deleted')
                                        print(now.strftime(
                                            "%Y-%m-%d %H:%M:%S") + ': ' + 'trying to delete the certificate created for the gateway')
                                        if len(host_arr_m1) > 0:
                                            event_deleted(fullEvent_dict)
                                        else:
                                            print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                        fullEvent_dict) + ' contains a domain which is not supported')
                                        #w.stop()
                                    else:
                                        now = datetime.datetime.now()
                                        resp = list_cert_details()
                                        cert_names = resp['cert_names']
                                        for count, each_server in enumerate(fullEvent_dict['servers']):
                                            count += 1
                                            if newEvent['Name'] + '-' + newEvent['Namespace'] + '-' + 'cert' + '-' + str(
                                                    count) in cert_names:
                                                print(now.strftime(
                                                    "%Y-%m-%d %H:%M:%S") + ': ' + "certificate already present for the gateway")
                                                print(now.strftime(
                                                    "%Y-%m-%d %H:%M:%S") + ': ' + 'Certificate found - so try to patch it')
                                                if len(host_arr_m1) > 0:
                                                    event_modified(fullEvent_dict)
                                                else:
                                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                        fullEvent_dict) + 'contains a domain which is not supported')

                                                #w.stop()
                                            else:
                                                try:
                                                    print(now.strftime(
                                                        "%Y-%m-%d %H:%M:%S") + ': ' + 'Certificate not found - so try to create it')
                                                    fullEvent_arr_p = []
                                                    host_arr_m2 = []
                                                    for server in event['object']['spec']['servers']:
                                                        if server['port']['protocol'] == 'HTTPS' or server['port']['protocol'] == 'TLS':
                                                            for hostname in server['hosts']:
                                                                if hostname.endswith(url_tuple):
                                                                    host_arr_m2.append(hostname)
                                                                else:
                                                                    print(
                                                                        now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                                            hostname) + ' the domain is not supported')
                                                            host_dict = {
                                                                'hostnames': host_arr_m2,
                                                                'secret_name': server['tls']['credentialName']
                                                            }

                                                            fullEvent = newEvent | host_dict
                                                            fullEvent_arr_p.append(fullEvent)

                                                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(fullEvent_arr_p))
                                                    if len(host_arr_m2) > 0:
                                                        for count, each_event in enumerate(fullEvent_arr_p):
                                                            event_added(each_event, count + 1)
                                                    else:
                                                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + str(
                                                                            fullEvent_arr_p) + 'contains a domain which is not supported')
                                                    #w.stop()
                                                except Exception as e:
                                                    print(now.strftime(
                                                        "%Y-%m-%d %H:%M:%S") + ': ' + 'Something went wrong- could not create '
                                                                                      'new cert ' + str(e))
                                                    #w.stop()

                            else:
                                print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "Required annotations are not present, "
                                                                                 "so the gateway - " +
                                      str(event['object']['metadata']['name']) + " is ignored")
                                #w.stop()

                        except Exception as e:
                            now = datetime.datetime.now()
                            print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + str(e))
                            #w.stop()
                    else:
                        now = datetime.datetime.now()
                        print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "resetting connection with kube api server")
                else:
                    now = datetime.datetime.now()
                    print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "closing the cycle")
                    sys.exit(1)
            except exceptions.ProtocolError:
                now = datetime.datetime.now()
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "resetting connection with kube api server")
            except client.exceptions.ApiException as e:
                now = datetime.datetime.now()
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "Resource version is too old. " + str(e))
                l1 = str(e)
                wl1 = l1.split()
                w1 = wl1[-1]
                rv = str(w1[1:-1])
                resource_version = rv
            except Exception as e:
                now = datetime.datetime.now()
                print(now.strftime("%Y-%m-%d %H:%M:%S") + ": " + "something went wrong with connection to kube api "
                                                                 "server. Restarting the pod. Error message - " + str(e) + str(type(e)))
                break

    except Exception as e:
        now = datetime.datetime.now()
        print(now.strftime("%Y-%m-%d %H:%M:%S") + ': ' + 'Something went wrong- please check logs ' + str(e))


if __name__ == "__main__":
    main()