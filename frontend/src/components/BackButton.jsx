// src/components/BackButton.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import "../styles/BackButton.css";

const BackButton = ({ label = "Volver" }) => {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(-1)}
      className="back-btn"
      type="button"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 22 22"
        fill="none"
        style={{ marginRight: "7px", verticalAlign: "middle" }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M14.5 18L8.5 12L14.5 6"
          stroke="#1976d2"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {label}
    </button>
  );
};

export default BackButton;
