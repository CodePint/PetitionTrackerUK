import React from "react";

function Petition404({ match }) {
  const petition_id = match.params.petition_id;

  return (
    <div className="petition NotFound">
      <div className="error-code">
        <h1>404</h1>
      </div>
      <div>
        <h2>Petition Not Found: {petition_id}</h2>
      </div>
    </div>
  );
}

export default Petition404;
