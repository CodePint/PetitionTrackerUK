import React, { useState, useEffect } from "react";
import moment from "moment";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPencilAlt, faCalendarAlt, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { BrowserRouter as Router, Link } from "react-router-dom";

function formatDate(date) {
  return moment(date).format("DD-MM-YYYY");
}

function PetitionItem({ item }) {
  return (
    <li className="PetitionItem">
      <div className="banner">
        <div className="id">
          <h4># {item.id}</h4>
        </div>
        <div className="external-link">
          <a href={item.url}>
            <span>
              <FontAwesomeIcon icon={faExternalLinkAlt} />
            </span>
          </a>
        </div>
      </div>

      <Link to={`/petition/${item.id}`}>
        <div className="wrapper">
          <div className="content">
            <h4>{item.action}</h4>
            <div className="background">
              <p>{item.background}</p>
            </div>
          </div>
          <div className="meta">
            <div>
              <span className="icon">
                <FontAwesomeIcon icon={faCalendarAlt} />
              </span>
              <span>{formatDate(item.pt_created_at)}</span>
            </div>

            <div>
              <span className="icon">
                <FontAwesomeIcon icon={faPencilAlt} />
              </span>
              <span>{item.signatures}</span>
            </div>
          </div>
        </div>
      </Link>
    </li>
  );
}

export default PetitionItem;
