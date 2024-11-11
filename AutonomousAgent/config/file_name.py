FILE_NAMES =  {
    "iot" : ["thing.private.key", "thing.cert.pem", "AmazonRootCA1.pem"], 
    "google" : ["google_credentials.json"], 
    "argument" : "arguments.json", 
    "prompt" :  "prompt_template.json"
}



IOT_CREDENTIALS_MAP = {
    "root_ca" : "AmazonRootCA1.pem",
    "thing_cert" : "thing.cert.pem",
    "private_key" : "thing.private.key"
}

GOOGLE_CREDENTIALS_MAP = {
    "credential" : "google_credentials.json"
}