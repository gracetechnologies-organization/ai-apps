from config import client

def get_Creds():
    try:
        db = client["AiDatabase"]
        collection = db["AWS_Coll"]
        document = collection.find_one()
        if document:
            # Extract values from the document
            service_name = document.get("SERVICE_NAME")
            region_name = document.get("REGION_NAME")
            aws_access_key = document.get("AWS_ACCESS_KEY")
            aws_secret_key = document.get("AWS_SECRET_KEY")

            return {
                "SERVICE_NAME": service_name,
                "REGION_NAME" : region_name,
                "AWS_ACCESS_KEY": aws_access_key,
                "AWS_SECRET_KEY": aws_secret_key,
            }
        else:
            print("No second document found in the collection.")

    except Exception as e:
        print(f"An error occurred while retrieving SD configuration: {e}")
    return None
