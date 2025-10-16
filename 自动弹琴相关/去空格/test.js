const fs = require('fs');
const path = require('path');

// 模拟文件操作的对象
const files = {
    listDir: function (dir, callback) {
        // 假设曲谱文件夹路径
        return fs.readdirSync(dir).filter(file => file.endsWith('.txt'));
    },
    open: function (filePath, mode, encoding) {
        return fs.createReadStream(filePath, { encoding: encoding });
    },
    join: path.join
};

// 方法定义
function __internal_fetchLocalSheets(listener) {
    const rootDir = './';  // 假设根目录是当前目录
    // const encoding = 'utf-8';
    const encoding = 'utf-16le'
    const sheets = files.listDir(rootDir, function (name) { return name.endsWith(".txt"); });
    this.cachedLocalSheetList = [];
    let failed = 0;

    for (let i in sheets) {
        try {
            const readable = files.open(path.join(rootDir, sheets[i]), "r", encoding);
            let data = '';
            readable.on('data', chunk => {
                data += chunk;
            });

            readable.on('end', () => {
                // 在这里输出读取的文件内容
                console.log(`Content of file ${sheets[i]}:`);
                console.log(data);  // 输出文件内容

                try {
                    const parsed = eval(data)[0];
                    if (typeof parsed.songNotes[0] === 'number' || parsed.isEncrypted) {
                        parsed.failed = true;
                        parsed.errtype = 1;
                        parsed.fileName = sheets[i];
                        parsed.reason = "It is a encrypted JSON sheet.";
                        failed++;
                    } else {
                        parsed.fileName = sheets[i];
                    }
                    this.cachedLocalSheetList.push(parsed);
                } catch (e) {
                    failed++;
                    this.cachedLocalSheetList.push({
                        failed: true,
                        errtype: (/illegal character/.test(String(e)) ? -1 : (/SyntaxError/.test(String(e)) ? 2 : -1)),
                        fileName: sheets[i],
                        reason: e
                    });
                }
                if (listener != null) listener(Number(i) + 1, failed);
            });

        } catch (e) {
            console.log(String(e));
            failed++;
            this.cachedLocalSheetList.push({
                failed: true,
                errtype: /illegal character/.test(String(e)) ? -1 : (/SyntaxError/.test(String(e)) ? 2 : -1),
                fileName: sheets[i],
                reason: e
            });
        }
    }
}

// 监听回调
function listener(index, failed) {
    console.log(`Processed ${index} files, ${failed} failed.`);
    if (failed > 0) {
        this.cachedLocalSheetList.forEach(sheet => {
            if (sheet.failed) {
                console.log(`File ${sheet.fileName} failed due to: ${sheet.reason}`);
            }
        });
    }
}

// 调用方法进行测试
__internal_fetchLocalSheets(listener);
