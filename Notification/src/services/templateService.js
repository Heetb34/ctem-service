const fs = require("fs");
const path = require("path");
function renderTemplate(templateName, data = {}, extension = "html") {
  const filePath = path.join(
    __dirname,
    "..",
    "templates",
    `${templateName}.${extension}`
  );
  let template = fs.readFileSync(filePath, "utf8");
  Object.keys(data).forEach((key) => {
    const regex = new RegExp(`{{${key}}}`, "g");
    template = template.replace(regex, data[key]);
  });
  return template;
}
module.exports = {
  renderTemplate,
};