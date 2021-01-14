import React, { useState } from "react";
import pic from "../assests/undraw_chat_bot_kli5.svg";
import {
  CustomInput,
  FormGroup,
  Container,
  Alert,
  Button,
  Modal,
  ModalBody,
  Spinner,
} from "reactstrap";
import axios from "axios";

const Build = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const [visible, setVisible] = useState(false);
  const onDismiss = () => setVisible(false);

  const [modal, setModal] = useState(false);
  const toggle = () => setModal(!modal);

  const submitFile = async () => {
    setModal(true);
    try {
      if (!file) {
        throw new Error("Select a file first!");
      }
      const formData = new FormData();
      console.log(file);
      formData.append("file", file[0]);
      await axios
        .post(`http://localhost:9000/test-upload`, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        })
        .then((res) => console.log(res.data));
      console.log("file uploaded");
      setTimeout(() => {
        setModal(false);
        setVisible(true);
      }, 7000);

      // handle success
    } catch (error) {
      // handle error
    }
  };

  return (
    // color="primary"
    <div>
      <Container>
        <h1 className="pt-4">Upload Configuration File </h1>
        <div className="d-flex justify-content-center pt-4">
          <FormGroup>
            <CustomInput
              type="file"
              onChange={(event) => setFile(event.target.files)}
            />
          </FormGroup>
          <div className="align-self-start pl-4">
            <Button
              style={{ backgroundColor: "#e3f2fd", color: "black" }}
              onClick={submitFile}
            >
              Upload
            </Button>
          </div>
        </div>
        <img
          className="pt-4"
          src={pic}
          style={{ height: "50%", width: "50%" }}
        />
        <Alert
          style={{ marginTop: "100px" }}
          color="success"
          isOpen={visible}
          toggle={onDismiss}
        >
          Your Lex chatbot was successfully generated in AWS cloud!
        </Alert>
      </Container>

      {/* loading modal */}
      <div>
        <Modal isOpen={modal} toggle={toggle}>
          {/* <ModalHeader toggle={toggle}>Generating Lex bot</ModalHeader> */}
          <ModalBody className="d-flex justify-content-center">
            <h3 style={{ color: "gray", marginRight: "20px" }}>
              Generating Lex Bot
            </h3>
            <Spinner color="primary" />
          </ModalBody>
        </Modal>
      </div>
    </div>
  );
};

export default Build;
