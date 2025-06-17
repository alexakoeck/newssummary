# newssummary

A news summarization agentic system for AWS environment using S3 and DynamoDB for storage. Articles are retrieved from secure websites and the previous summaries stored in the S3 bucket.

sudo apt update && sudo apt install python3-pip -y

pip3 install -r requirements.txt --break-system-packages

python3 -m spacy download en_core_web_sm --break-system-packages
