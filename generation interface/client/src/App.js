import "./App.css";
import AppBar from "./components/AppBar";
import Build from "./pages/Build";
import Documentation from "./pages/Documentation";
import { BrowserRouter as Router, Route } from "react-router-dom";

function App() {
  return (
    <div className="App">
      <AppBar />
      <Router>
        <Route path="/" component={Build} exact />
        <Route path="/documentation" component={Documentation} />
      </Router>
    </div>
  );
}

export default App;
