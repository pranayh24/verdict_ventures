const express = require("express");
const app = express();
const path = require("path");
const ejsMate = require("ejs-mate");
const methodOverride = require("method-override");

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.urlencoded({extended : true}));
app.use(methodOverride("_method"));
app.engine("ejs", ejsMate);

app.use(express.static(path.join(__dirname, "/public")));


app.listen(8080, () => {
    console.log("Server is listening to port 8080");
});

app.get("/home", (req, res) => {
    res.render("pages/front.ejs");
});

app.get("/acts", (req, res) => {
    res.render("pages/act.ejs");
});

app.get("/acts/chap1", (req, res) => {
    res.render("pages/acts1.ejs");
});

app.get("/acts/chap2", (req, res) => {
    res.render("pages/acts2.ejs");
});

app.get("/acts/chap3", (req, res) => {
    res.render("pages/acts3.ejs");
});

app.get("/acts/chap3a", (req, res) => {
    res.render("pages/acts3a.ejs");
});

app.get("/acts/chap4", (req, res) => {
    res.render("pages/acts4.ejs");
});

app.get("/acts/chap5", (req, res) => {
    res.render("pages/acts5.ejs");
});

app.get("/acts/chap6", (req, res) => {
    res.render("pages/acts6.ejs");
});

app.get("/acts/chap7", (req, res) => {
    res.render("pages/acts7.ejs");
});

app.get("/work", (req, res) => {
    res.render("pages/work.ejs");
});

app.get("/ethics", (req, res) => {
    res.render("pages/ethics.ejs");
});

app.get("/form", (req, res) => {
    res.render("pages/form.ejs");
});

