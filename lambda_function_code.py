import json
import base64
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
import boto3
import os

print('Loading function')

def lambda_handler(event, context):
    produce_messages_from_event(event)

    
def deserialize_message(message):
    decoded_value = base64.b64decode(message)
    avro_deserializer = AvroDeserializer(SCHEMA_REGISTRY_CLIENT)
    deserialized_value = avro_deserializer(decoded_value, None)
    return deserialized_value

def produce_messages_from_event(event):
    records = event['records']
    for topic_partition_key in records:
        topic_partition_list = records[topic_partition_key]
        for message in topic_partition_list:
            deserialized_message = deserialize_message(message['value'])
            normalised_message= normalise_message(deserialized_message)
            produce_message(normalised_message)

def produce_message(message):
    try:
        key = message.get('ORIGIN')
        PRODUCER.produce('final', key, message)
        print(f'Message produced to kafka:  {message} ')
    except Exception as e:
        print(f"Exception while producing message - {message} : {e}")
    PRODUCER.flush()
    

def create_avro_producer():
    schemaDetails = SCHEMA_REGISTRY_CLIENT.get_latest_version('final-value')
    schema = schemaDetails.schema.schema_str
    producer = SerializingProducer({
            'bootstrap.servers': bootstrap_servers,
            'sasl.mechanisms': 'PLAIN',
            'security.protocol': 'SASL_SSL',
            'sasl.username': sasl_username,
            'sasl.password': sasl_password,
            'key.serializer': StringSerializer(),
            'value.serializer': AvroSerializer(SCHEMA_REGISTRY_CLIENT, schema),
            'client.id': 'aws-lambda',
            'batch.size': 5000
        })
    return producer
    
def normalise_address(addresses):
    index=0
    for address in addresses:
        addresses[index]['CITY'] = address['CITY'].strip().title()
        addresses[index]['STATE'] = address['STATE'].strip().upper()
        addresses[index]['STREETNAME'] = ''.join([i for i in address['STREETNAME'] if not i.isdigit()]).strip()
        index+=1

def normalise_message(message):
    Applicants = message['APPLICANTS']
    for applicant in Applicants:
        normalise_address(applicant['ADDRESSHISTORY'])
        normalise_address([applicant['EMPLOYMENTDETAILS']['EMPLOYERADDRESS']])
    normalise_address([message['PROPERTYADDRESS']])
    return message
    
def decrypt_env_var(env_var_name):
    ENCRYPTED = os.environ[env_var_name]
    DECRYPTED = boto3.client('kms').decrypt(CiphertextBlob=base64.b64decode(ENCRYPTED),
    EncryptionContext={'LambdaFunctionName': 'aws-normalise-demo-lambda'})['Plaintext'].decode('utf-8')
    return DECRYPTED


SCHEMA_REGISTRY_CLIENT = SchemaRegistryClient({ 'url': decrypt_env_var('schema_registry_url'), 'basic.auth.user.info': decrypt_env_var('basic_auth_user_info')})
sasl_username = decrypt_env_var('sasl_username')
sasl_password = decrypt_env_var('sasl_password')
bootstrap_servers = decrypt_env_var('bootstrap_servers')
PRODUCER = create_avro_producer()