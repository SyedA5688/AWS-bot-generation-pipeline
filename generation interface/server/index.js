const express = require("express");
const AWS = require("aws-sdk");
const fs = require("fs");
const fileType = require("file-type");
const cors = require("cors");
const multiparty = require("multiparty");
const {
  S3_BUCKET,
  AWS_ACCESS_KEY_ID,
  AWS_SECRET_ACCESS_KEY,
  AWS_SESSION_TOKEN,
} = require("./credentials.js");

const app = express();
app.use(cors());

AWS.config.update({
  accessKeyId: AWS_ACCESS_KEY_ID,
  secretAccessKey: AWS_SECRET_ACCESS_KEY,
  sessionToken: AWS_SESSION_TOKEN,
});

// create S3 instance
const s3 = new AWS.S3();

const uploadFile = (buffer, name, type) => {
  const params = {
    ACL: "public-read",
    Body: buffer,
    Bucket: S3_BUCKET,
    ContentType: "text/yaml",
    Key: `${name}`,
  };
  //console.log(params);
  return s3.upload(params).promise();
};

// Define POST route
app.post("/test-upload", (request, response) => {
  const form = new multiparty.Form();
  form.parse(request, async (error, fields, files) => {
    if (error) {
      return response.status(500).send(error);
    }
    try {
      const path = files.file[0].path;
      const buffer = fs.readFileSync(path);
      const type = await fileType.fromBuffer(buffer);
      const fileName = `input/${files.file[0].originalFilename}`;
      const data = await uploadFile(buffer, fileName, type);
      return response.status(200).send(data);
    } catch (err) {
      console.log(err);
      return response.status(500).send(err);
    }
  });
});

app.listen(process.env.PORT || 9000);

console.log(`Server running on port ${process.env.PORT || 9000}`);
