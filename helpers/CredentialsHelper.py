from config import collection, client

def get_Creds():
    try:
        document = collection.find_one(skip=1)
        if document:
            # Extract values from the document
            s3_bucket = document.get("S3_BUCKET")
            aws_access_key = document.get("AWS_ACCESS_KEY")
            aws_secret_key = document.get("AWS_SECRET_KEY")
            diffusion_key = document.get("DIFFUSION_KEY")

            return {
                "S3_BUCKET": s3_bucket,
                "AWS_ACCESS_KEY": aws_access_key,
                "AWS_SECRET_KEY": aws_secret_key,
                "DIFFUSION_KEY": diffusion_key
            }
        else:
            print("No second document found in the collection.")

    except Exception as e:
        print(f"An error occurred while retrieving SD configuration: {e}")
    return None
