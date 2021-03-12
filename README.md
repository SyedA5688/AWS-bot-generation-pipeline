# AWS-bot-generation-pipeline

This project aims to create a pipeline for rapid chatbot creation and deployment using AWS
services. The React frontend receives a configuration file with the conversation pattern
and specifications desired for the chatbot, and the pipeline then takes care of generating
and building the bot by sending the configuration file to a S3 bucket instance and using
lambda triggers to begin bot creation.

# Goal

The goal of this project is to reduce the human supervision and task management needed
in areas such as information retrieval and transaction processing. Utilizing chatbots more
can help business improve their margins and avoid cost and resource overhead from maintaining
information specialists and customer service agents.

# Botathon Team
- Nykolas Farhangi
- Syed Rizvi
- Muhammad Usman
- Ross Koepke

# Link to Demo Video
Youtube: https://www.youtube.com/watch?v=EfDlcgntEl0&t=7s

This project was developed for the HP & AWS bot-a-thon competition. The project placed 1st overall.

![HP Botathon Certificate](/assets/HP_certificate.png)

# Bot pipeline architecture
![Bot pipeline architecture](/assets/bot_architecture_diagram.png)

# AWS Services Used
- AWS Lex
- AWS Lambda
- DynamoDB
- S3 bucket instances
