const fs = require("fs");
const path = "./致爱丽丝（1）.txt";  // 文件路径

// 读取文件内容
fs.readFile(path, "utf-8", (err, data) => {
  if (err) {
    console.error("读取文件失败:", err);
    return;
  }

  // 去掉换行符和空格
  const cleaned = data.replace(/\s+/g, "");

  // 保存到新文件，也可以直接覆盖原文件
  fs.writeFile("./致爱丽丝_cleaned1.txt", cleaned, "utf-8", (err) => {
    if (err) {
      console.error("写入文件失败:", err);
      return;
    }
    console.log("处理完成，结果已保存到 致爱丽丝_cleaned.txt");
  });
});
