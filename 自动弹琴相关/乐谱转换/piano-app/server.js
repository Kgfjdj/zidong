const express = require('express');
const multer = require('multer');
const MidiParser = require('midi-parser-js');
const fs = require('fs');
const path = require('path');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(express.static('.'));
app.use(express.json());

// 解析 MIDI 文件
app.post('/parse-midi', upload.single('midiFile'), (req, res) => {
  try {
    const midiFile = fs.readFileSync(req.file.path);
    const midiArray = new Uint8Array(midiFile);
    const parsed = MidiParser.parse(midiArray);
    
    fs.unlinkSync(req.file.path);
    
    res.json(parsed);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 保存编辑后的 MIDI 文件
app.post('/save-midi', (req, res) => {
  try {
    const { midiData, fileName } = req.body;
    
    // 将编辑后的数据转换为 MIDI 文件
    const midiBytes = createMidiFile(midiData);
    
    // 保存到临时目录
    const outputPath = path.join('uploads', fileName || 'edited.mid');
    fs.writeFileSync(outputPath, Buffer.from(midiBytes));
    
    // 发送文件给客户端
    res.download(outputPath, fileName || 'edited.mid', (err) => {
      // 下载完成后删除临时文件
      if (fs.existsSync(outputPath)) {
        fs.unlinkSync(outputPath);
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 转换 MIDI 为 JSON 格式(用于编辑)
app.post('/midi-to-json', upload.single('midiFile'), (req, res) => {
  try {
    const midiFile = fs.readFileSync(req.file.path);
    const midiArray = new Uint8Array(midiFile);
    const parsed = MidiParser.parse(midiArray);
    
    // 转换为更易编辑的格式
    const editableFormat = convertToEditableFormat(parsed);
    
    fs.unlinkSync(req.file.path);
    
    res.json(editableFormat);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 将解析的 MIDI 转换为可编辑格式
function convertToEditableFormat(parsed) {
  const tracks = parsed.track.map((track, trackIndex) => {
    const notes = [];
    let currentTime = 0;
    
    track.event.forEach(event => {
      currentTime += event.deltaTime;
      
      if (event.type === 9 && event.data && event.data[1] > 0) { // Note On
        notes.push({
          time: currentTime,
          note: event.data[0],
          velocity: event.data[1],
          duration: 0, // 需要在 Note Off 时计算
          channel: event.channel
        });
      } else if ((event.type === 8 || (event.type === 9 && event.data[1] === 0))) { // Note Off
        // 找到对应的 Note On 并设置持续时间
        const noteOn = notes.reverse().find(n => n.note === event.data[0] && n.duration === 0);
        if (noteOn) {
          noteOn.duration = currentTime - noteOn.time;
        }
        notes.reverse();
      }
    });
    
    return {
      trackIndex,
      notes: notes.filter(n => n.duration > 0)
    };
  });
  
  return {
    timeDivision: parsed.timeDivision,
    tracks: tracks.filter(t => t.notes.length > 0)
  };
}

// 创建 MIDI 文件字节
function createMidiFile(midiData) {
  const header = [0x4D, 0x54, 0x68, 0x64]; // "MThd"
  const headerLength = [0x00, 0x00, 0x00, 0x06];
  const format = [0x00, 0x01]; // Format 1
  const trackCount = [0x00, midiData.tracks.length];
  const timeDivision = [
    (midiData.timeDivision >> 8) & 0xFF,
    midiData.timeDivision & 0xFF
  ];
  
  let result = [...header, ...headerLength, ...format, ...trackCount, ...timeDivision];
  
  midiData.tracks.forEach(track => {
    const trackData = createTrackData(track, midiData.timeDivision);
    result = result.concat(trackData);
  });
  
  return new Uint8Array(result);
}

// 创建音轨数据
function createTrackData(track, timeDivision) {
  const trackHeader = [0x4D, 0x54, 0x72, 0x6B]; // "MTrk"
  let events = [];
  
  // 按时间排序音符
  const sortedNotes = [...track.notes].sort((a, b) => a.time - b.time);
  
  let lastTime = 0;
  sortedNotes.forEach(note => {
    // Note On
    const deltaTime = note.time - lastTime;
    events = events.concat(encodeVariableLength(deltaTime));
    events.push(0x90, note.note, note.velocity); // Note On
    
    // Note Off
    events = events.concat(encodeVariableLength(note.duration));
    events.push(0x80, note.note, 0x40); // Note Off
    
    lastTime = note.time + note.duration;
  });
  
  // End of Track
  events = events.concat([0x00, 0xFF, 0x2F, 0x00]);
  
  const trackLength = [
    (events.length >> 24) & 0xFF,
    (events.length >> 16) & 0xFF,
    (events.length >> 8) & 0xFF,
    events.length & 0xFF
  ];
  
  return [...trackHeader, ...trackLength, ...events];
}

// 编码可变长度值
function encodeVariableLength(value) {
  const bytes = [];
  bytes.push(value & 0x7F);
  value >>= 7;
  
  while (value > 0) {
    bytes.unshift((value & 0x7F) | 0x80);
    value >>= 7;
  }
  
  return bytes;
}

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
