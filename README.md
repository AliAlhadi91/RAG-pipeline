# AI Lawyer 

# Create Conda Env
```bash
conda create -n ai-lawyer python=3.10
```

# Activate Conda Env
```bash
conda activate ai-lawyer
```

# Install requirements
```bash
pip install -r requirements.txt

```
# AI-Lawyer full pipeline
## 1.Scrapping pipeline
### a-The scrapping pipeline consists of the 3 files scrapping.py to collect the rulings_yearnb.json for each year you specify the json file contains all judgments for specific year as objects {
    link-->link for this specific judgment
    title
    list of tags
    link_to_full_document --> Link to actual pdf for ocr later
    summary --> summary of this specific judgment
}
### b-upload_to_s3 that downloads the necessary pdf files from the link_to_full_document and upload them to s3 bucket ai-lawyer-judgments-raw-pdf
### c-transform.py that divides each pdf into images and also upload them to another s3 bucket ai-lawyer-judgments-images for later processing

## 2.Cleaning pipeline
### a-the cleaning pipeline includes downloading the images from the above s3 bucket for processing
### b-use the layout-detector model to detect if the image is 1-column or 2-column 
### if 1 column:keep it as it is
### if 2 column:divide to parts and process each one seperately
### c-ocr.py to using document-ai to apply ocr on the images we have and upload the json files we get after the ocr to ai-lawyer-judgments-ocr-json s3 bucket and also we get txt file for each image 
### d-merge.py merge the txt files that belong to the same judgment 
### Finally we have ==> year/file_nb.txt
### e-clean_and_upload it uses camel tools (https://camel-tools.readthedocs.io/en/latest/cli/camel_arclean.html)
### to clean the txt files we have then upload them to s3 bucket ai-lawyer-judgments-cleaned

## 3.chunking_and_embedding
### Ok in the chunking_and_embedding folder we have the following parts:
### a-download_from_s3.py that downloads the cleaned txt files to apply chunking on them from s3 buckt ai-lawyer-judgments-cleaned
### b-semantic_chunking.py that uses windows and embed each one to compare with the next window and according to that determines the correct size for each chunk according to certain similarity thresold with its next windows and so on ( you can find more details in the code or from this link https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb)
### c-embed_chunks.py use genai api key to embed chunks we made using gemini-embedding-001 model and add those vectors for each chunk to save them to the weaviate database later
### d-upload_vectors.py it uploads the vectors we have along with the chunks and some metadata for each chunk for example list of tags,title...
### uploads them to s3 bucket in case we wanted to change the vectordatabase were using
### also uploads them to weaviate collection called LegalChunks as the follow:
### obj = {
            "chunk": item.get("chunk"),
            "link": item.get("link"),
            "title": item.get("title"),
            "list":item.get("list"),
            "full_document": item.get("full_document"),
            "path": file_path_str,
            "index": item.get("index")
        }
### also adding to them the 3072-vector from gemini after embedding


# How to run the full pipeline
```bash 
python full_pipeline.py --years year_nb_1 year_nb_2 ....
```

# To run each pipeline seperately 
## Scrapping pipeline
```bash

python scrappers/lu_scrapper/main.py --years year_nb_1 year_nb_2....

```

## Cleaning pipeline
```bash

python cleaning/main.py --years year_nb_1 year_nb_2....

```

## Scrapping pipeline
```bash

python chunking_and_embedding/main.py --years year_nb_1 year_nb_2....

```
