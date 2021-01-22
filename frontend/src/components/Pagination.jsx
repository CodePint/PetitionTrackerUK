import React, { useState, useEffect, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ReactPaginate from "react-paginate";

import _ from "lodash";

function Pagination({ pages, baseUrl, urlParams, pagesToShow, pageChangeHandler = null }) {
  function render() {
    if (!_.isEmpty(pages)) {
      return (
        <ReactPaginate
          previousLabel={"<"}
          nextLabel={">"}
          breakLabel={"..."}
          breakClassName={"break-me"}
          pageCount={pages.last.index}
          marginPagesDisplayed={1}
          pageRangeDisplayed={pagesToShow}
          onPageChange={pageChangeHandler}
          containerClassName={"pagination"}
          subContainerClassName={"pages pagination"}
          activeClassName={"active"}
          initialPage={pages.curr.index - 1}
        />
      );
    }
  }

  return <div className="Pagination">{render()}</div>;
}
export default Pagination;
