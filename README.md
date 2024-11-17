# Seeker-Agent 🔎

Searching through websites and blogs for a single piece of reliable information can often be tedious. I mean, who loves scrolling endlessly to find what you need in some corner of a 7 year old webpage. Ever wished for Large Language Models to get this done for you?

That's exactly what this project brings, the power of Google Search, now with the same model behind ChatGPT. With the **Seeker Agent**, now you can simply upload your data as a `.csv` file or connect your Google Sheet, ask a question about your data, sit back and let **Seeker Agent** do the heavylifting for you. Several minutes of tiring Web Search, done in a minute (that's faster than your noodles get prepared in!), but that's not all. With a single click, you can update all of the new found information from the web, back to your data file. It's really that simple.

### Getting Started 🚀

If you have been thinking that to have access to such ease comes with a painful setup, you would be mistaken. Setting up **Seeker Agent** is easier than you could imagine!

```
cd your_favourite_repository
git clone https://github.com/debdeepsanyal/Seeker-Agent.git
cd seeker-agent
touch .env
echo "OPENAI_API_KEY=<your OpenAI API KEY>\nSERPAPI_API_KEY=<your SerpAPI API key>" > .env
streamlit run main.py
```

and, that's all! Executing the above few lines in your terminal opens up a functional and user-friendly interface, which gets all your done in a few clicks. 

### Usage Notes 🚨
Due to some API restrictions, we (unfortunately) have to limit some of the utilities. The column of the file you are uploading, be it your `.csv` file or the Google Sheet, should have <= **5** unique values. Since we have to perform a Web Search for each of the values, we are limitting the same. The software can automatically detect and will notify you if your chosen column has more than the allowed number of unique values.

If you wish to connect to your Google Sheets, you need to have a `JSON keyfile`, which is required in order to establish the connection. The easiest way to get it done is follow the steps as [instructed by Google](https://developers.google.com/workspace/guides/get-started). Note that you must be creating a `Service Account`, and once you are done creating the same and enabling the API for Google Sheets (all of this is documented in the aforementioned link), in the 5th step of the process, you will head to the **Credentials** page, where you will find your account under `Service Accounts`. Click on the same, and you will land at a `Trial` page. Click on the `KEYS` tab above, click on `ADD KEY`, `Create new key`, and then `JSON`. That's all! This is the JSON file that you need to upload to the software while establishing the connection. 

Also ensure that before sharing the link to your Google Sheet, you have shared your Google Sheet with the `Service Account` you created (it will be something in the form of `some-name.gserviceaccount.com`), and add this account as the **Editor** to your Google Sheet. Once you have set this up, you're all set!