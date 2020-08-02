import React, { useState, useEffect } from 'react';
import logo from './logo.svg';
import './App.css';

function App() {
  const [currentTime, setCurrentTime] = useState('N/A');
  const [flaskResponse, setFlaskResponse] = useState('FAIL');


  useEffect(() => {
    fetch('/react_flask_test').then(res => res.json()).then(data => {
      setCurrentTime(data.time);
      setFlaskResponse(data.response);
    });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
      <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React!
        </a>
        <p>Flask API: {flaskResponse}, at: {currentTime}.</p>
      </header>
    </div>
  );
}

export default App;