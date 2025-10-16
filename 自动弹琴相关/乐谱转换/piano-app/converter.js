class MIDIConverter {
    constructor() {
        this.midiData = null;
        this.convertedData = null;
        this.fileName = ''; // 添加文件名属性
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.player = new WebAudioFontPlayer();
        this.instrument = _tone_0250_SoundBlasterOld_sf2;
        this.isPlaying = false;
        this.playbackSpeed = 1.0;
        this.playTimeouts = [];
        this.cursorAnimationFrame = null; // 添加这一行

        this.player.loader.decodeAfterLoading(this.audioContext, '_tone_0250_SoundBlasterOld_sf2');

        this.initControls();
        this.initGrid();
    }

    initControls() {
        const midiFileInput = document.getElementById('midiFile');
        const convertBtn = document.getElementById('convertBtn');
        const playBtn = document.getElementById('playBtn');
        const stopBtn = document.getElementById('stopBtn');
        const downloadBtn = document.getElementById('downloadBtn');
        const speedControl = document.getElementById('speedControl');

        midiFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadMIDI(file);
            }
        });

        convertBtn.addEventListener('click', () => this.convert());
        playBtn.addEventListener('click', () => this.play());
        stopBtn.addEventListener('click', () => this.stop());
        downloadBtn.addEventListener('click', () => this.download());

        speedControl.addEventListener('input', (e) => {
            this.playbackSpeed = parseFloat(e.target.value);
            document.getElementById('speedValue').textContent = `${this.playbackSpeed.toFixed(1)}x`;
        });
    }

    initGrid() {
        const grid = document.getElementById('grid');
        const keys = 37;
        const bitsPerPage = 16;

        grid.innerHTML = '<div class="grid-header">轨道</div>';
        for (let i = 0; i < bitsPerPage; i++) {
            const isBeat = i % 4 === 0;
            grid.innerHTML += `<div class="grid-header ${isBeat ? 'beat-marker' : ''}">${i}</div>`;
        }

        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        for (let i = keys; i >= 1; i--) {
            const midiNote = 48 + (i - 1);
            const noteName = noteNames[(midiNote) % 12] + Math.floor(midiNote / 12 - 1);

            grid.innerHTML += `<div class="grid-row" title="MIDI ${midiNote}">${noteName}<br>1Key${i}</div>`;

            for (let j = 0; j < bitsPerPage; j++) {
                const isBeat = j % 4 === 0;
                grid.innerHTML += `<div class="grid-cell ${isBeat ? 'beat-marker' : ''}" data-key="${i}" data-time="${j}"></div>`;
            }
        }
    }

    async loadMIDI(file) {
        try {
            const formData = new FormData();
            formData.append('midiFile', file);

            // 保存文件名(去掉扩展名)
            this.fileName = file.name.replace(/\.(mid|midi)$/i, '');

            const response = await fetch('/parse-midi', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('服务器解析失败');
            }

            this.midiData = await response.json();

            document.getElementById('convertBtn').disabled = false;

            const info = document.getElementById('fileInfo');
            info.innerHTML = `
                <div class="info-item"><strong>文件名:</strong> ${file.name}</div>
                <div class="info-item"><strong>轨道数:</strong> ${this.midiData.track.length}</div>
                <div class="info-item"><strong>时间分辨率:</strong> ${this.midiData.timeDivision} ticks/beat</div>
            `;

            alert('MIDI 文件加载成功!');
        } catch (error) {
            alert('MIDI 文件加载失败: ' + error.message);
            console.error(error);
        }
    }

    convert() {
        if (!this.midiData) return;

        const songNotes = [];
        const ticksPerBeat = this.midiData.timeDivision;
        let tempo = 500000; // 默认 120 BPM

        const allEvents = [];
        this.midiData.track.forEach((track, trackIndex) => {
            let currentTick = 0;
            track.event.forEach(event => {
                currentTick += event.deltaTime;
                allEvents.push({
                    tick: currentTick,
                    type: event.type,
                    data: event.data,
                    trackIndex
                });
            });
        });

        allEvents.sort((a, b) => a.tick - b.tick);

        // 查找 Tempo 事件 (Meta Event 0x51)
        const tempoEvent = allEvents.find(e => e.type === 255 && e.data && e.data[0] === 81);
        if (tempoEvent && tempoEvent.data.length >= 4) {
            tempo = (tempoEvent.data[1] << 16) | (tempoEvent.data[2] << 8) | tempoEvent.data[3];
        }

        const bpm = Math.round(60000000 / tempo);
        const msPerTick = tempo / ticksPerBeat / 1000;

        // 转换音符
        allEvents.forEach(event => {
            const timeMs = Math.round(event.tick * msPerTick);

            // Note On (type 9, velocity > 0)
            if (event.type === 9 && event.data && event.data[1] > 0) {
                const midiNote = event.data[0];
                let num = 0;

                // C3(48) 到 C6(84) 映射到 1Key1-1Key37
                // if (midiNote >= 48 && midiNote <= 84) {
                //     const keyNumber = midiNote - 48 + 1
                // if (midiNote >= 48 + 10 && midiNote <= 84 + 10) {
                //     const keyNumber = midiNote - 48 + 1-12
                if (midiNote >= 48 + num && midiNote <= 84 + num) {
                    const keyNumber = midiNote - 48 - num;
                    songNotes.push({
                        time: timeMs,
                        key: `1Key${keyNumber}`,
                        midi: midiNote
                    });
                }
            }
        });

        songNotes.sort((a, b) => a.time - b.time);

        this.convertedData = {
            name: this.fileName,
            bpm: bpm,
            bitsPerPage: 16,
            pitchLevel: 0,
            songNotes: songNotes
        };

        const output = document.getElementById('output');
        const displayData = {
            ...this.convertedData,
            songNotes: this.convertedData.songNotes.map(note => ({
                time: note.time,
                key: note.key
            }))
        };
        output.textContent = JSON.stringify(displayData, null, 2);

        this.updateGrid();

        document.getElementById('playBtn').disabled = false;
        document.getElementById('downloadBtn').disabled = false;

        alert(`转换完成!\n音符数: ${songNotes.length}\nBPM: ${bpm}\n范围: C3-C6 (1Key1-1Key37)`);
    }

    // convert() {
    //     if (!this.midiData) return;

    //     const songNotes = [];
    //     const ticksPerBeat = this.midiData.timeDivision;
    //     let tempo = 500000; // 默认 120 BPM

    //     const allEvents = [];
    //     this.midiData.track.forEach((track, trackIndex) => {
    //         let currentTick = 0;
    //         track.event.forEach(event => {
    //             currentTick += event.deltaTime;
    //             allEvents.push({
    //                 tick: currentTick,
    //                 type: event.type,
    //                 data: event.data,
    //                 trackIndex
    //             });
    //         });
    //     });

    //     allEvents.sort((a, b) => a.tick - b.tick);

    //     // 查找 Tempo 事件 (Meta Event 0x51)
    //     const tempoEvent = allEvents.find(e => e.type === 255 && e.data && e.data[0] === 81);
    //     if (tempoEvent && tempoEvent.data.length >= 4) {
    //         tempo = (tempoEvent.data[1] << 16) | (tempoEvent.data[2] << 8) | tempoEvent.data[3];
    //     }

    //     const bpm = Math.round(60000000 / tempo);
    //     const msPerTick = tempo / ticksPerBeat / 1000;

    //     // 转换音符
    //     allEvents.forEach(event => {
    //         const timeMs = Math.round(event.tick * msPerTick);

    //         // Note On (type 9, velocity > 0)
    //         if (event.type === 9 && event.data && event.data[1] > 0) {
    //             const midiNote = event.data[0];

    //             // C3(48) 到 C6(84) 映射到 1Key1-1Key37
    //             if (midiNote >= 48 && midiNote <= 84) {
    //                 const keyNumber = midiNote - 48 + 1;
    //                 songNotes.push({
    //                     time: timeMs,
    //                     key: `1Key${keyNumber}`,
    //                     midi: midiNote
    //                 });
    //             }
    //         }
    //     });

    //     songNotes.sort((a, b) => a.time - b.time);

    //     this.convertedData = {
    //         bpm: bpm,
    //         bitsPerPage: 16,
    //         pitchLevel: 0,
    //         songNotes: songNotes
    //     };

    //     const output = document.getElementById('output');
    //     const displayData = {
    //         ...this.convertedData,
    //         songNotes: this.convertedData.songNotes.map(note => ({
    //             time: note.time,
    //             key: note.key
    //         }))
    //     };
    //     output.textContent = JSON.stringify(displayData, null, 2);

    //     this.updateGrid();

    //     document.getElementById('playBtn').disabled = false;
    //     document.getElementById('downloadBtn').disabled = false;

    //     alert(`转换完成!\n音符数: ${songNotes.length}\nBPM: ${bpm}\n范围: C3-C6 (1Key1-1Key37)`);
    // }

    // updateGrid() {
    //     if (!this.convertedData) return;

    //     const grid = document.getElementById('grid');
    //     const keys = 37;
    //     const bitsPerPage = 16;

    //     // 计算需要多少页（每页16格）
    //     const totalDuration = this.convertedData.songNotes.length > 0
    //         ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
    //         : 0;

    //     const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
    //     const totalBits = Math.ceil(totalDuration / msPerBit);
    //     const totalPages = Math.ceil(totalBits / bitsPerPage);
    //     const totalColumns = totalPages * bitsPerPage;

    //     // 清空并重建网格
    //     grid.innerHTML = '';
    //     grid.style.gridTemplateColumns = `60px repeat(${totalColumns}, 40px)`;

    //     // 创建表头
    //     grid.innerHTML += '<div class="grid-header">轨道</div>';
    //     for (let i = 0; i < totalColumns; i++) {
    //         const isBeat = i % 4 === 0;
    //         const isPageStart = i % bitsPerPage === 0;
    //         const pageNum = Math.floor(i / bitsPerPage) + 1;
    //         const bitInPage = i % bitsPerPage;

    //         grid.innerHTML += `<div class="grid-header ${isBeat ? 'beat-marker' : ''} ${isPageStart ? 'page-start' : ''}" 
    //                             title="页${pageNum} - 格${bitInPage}">${bitInPage}</div>`;
    //     }

    //     // 创建音符行
    //     const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    //     for (let i = keys; i >= 1; i--) {
    //         const midiNote = 48 + (i - 1);
    //         const noteName = noteNames[(midiNote) % 12] + Math.floor(midiNote / 12 - 1);

    //         grid.innerHTML += `<div class="grid-row" title="MIDI ${midiNote}">${noteName}<br>1Key${i}</div>`;

    //         for (let j = 0; j < totalColumns; j++) {
    //             const isBeat = j % 4 === 0;
    //             const isPageStart = j % bitsPerPage === 0;
    //             grid.innerHTML += `<div class="grid-cell ${isBeat ? 'beat-marker' : ''} ${isPageStart ? 'page-start' : ''}" 
    //                                 data-key="${i}" data-time="${j}"></div>`;
    //         }
    //     }

    //     // 填充音符
    //     this.convertedData.songNotes.forEach(note => {
    //         const keyMatch = note.key.match(/1Key(\d+)/);
    //         if (!keyMatch) return;

    //         const keyNumber = parseInt(keyMatch[1]);
    //         const bitPosition = Math.floor(note.time / msPerBit);

    //         const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
    //         if (cell) {
    //             cell.classList.add('has-note');
    //             const pageNum = Math.floor(bitPosition / bitsPerPage) + 1;
    //             const bitInPage = bitPosition % bitsPerPage;
    //             cell.title = `${note.key} @ ${note.time}ms\n页${pageNum} 格${bitInPage}`;
    //         }
    //     });

    //     // 显示统计信息
    //     console.log(`网格信息: 总时长=${totalDuration}ms, 总格数=${totalColumns}, 总页数=${totalPages}`);
    // }

    // updateGrid() {
    //     document.querySelectorAll('.grid-cell').forEach(cell => {
    //         cell.classList.remove('has-note');
    //     });

    //     if (!this.convertedData) return;

    //     const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;

    //     this.convertedData.songNotes.forEach(note => {
    //         const keyMatch = note.key.match(/1Key(\d+)/);
    //         if (!keyMatch) return;

    //         const keyNumber = parseInt(keyMatch[1]);
    //         const bitPosition = Math.floor(note.time / msPerBit) % 16;

    //         const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
    //         if (cell) {
    //             cell.classList.add('has-note');
    //             cell.title = `${note.key} @ ${note.time}ms`;
    //         }
    //     });
    // }



    // play() {
    //     if (!this.convertedData || this.isPlaying) return;

    //     this.isPlaying = true;
    //     document.getElementById('playBtn').disabled = true;
    //     document.getElementById('stopBtn').disabled = false;
    //     document.getElementById('progressBar').style.display = 'block';

    //     const totalDuration = this.convertedData.songNotes.length > 0
    //         ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
    //         : 0;

    //     this.convertedData.songNotes.forEach(note => {
    //         const delay = note.time / this.playbackSpeed;

    //         const timeout = setTimeout(() => {
    //             this.player.queueWaveTable(
    //                 this.audioContext,
    //                 this.audioContext.destination,
    //                 this.instrument,
    //                 this.audioContext.currentTime,
    //                 note.midi,
    //                 0.5,
    //                 0.7
    //             );

    //             const keyMatch = note.key.match(/1Key(\d+)/);
    //             if (keyMatch) {
    //                 const keyNumber = parseInt(keyMatch[1]);
    //                 const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
    //                 const bitPosition = Math.floor(note.time / msPerBit) % 16;

    //                 const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
    //                 if (cell) {
    //                     cell.classList.add('active');
    //                     setTimeout(() => cell.classList.remove('active'), 200);
    //                 }
    //             }

    //             const progress = (note.time / totalDuration) * 100;
    //             document.getElementById('progressFill').style.width = `${progress}%`;
    //         }, delay);

    //         this.playTimeouts.push(timeout);
    //     });

    //     const endTimeout = setTimeout(() => {
    //         this.stop();
    //     }, totalDuration / this.playbackSpeed + 1000);

    //     this.playTimeouts.push(endTimeout);
    // }

    updateGrid() {
        if (!this.convertedData) return;

        const grid = document.getElementById('grid');
        const keys = 37;
        const bitsPerPage = 16;

        // 计算需要多少页
        const totalDuration = this.convertedData.songNotes.length > 0
            ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
            : 0;

        const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
        const totalBits = Math.ceil(totalDuration / msPerBit) + bitsPerPage; // 多加一页缓冲
        const totalPages = Math.ceil(totalBits / bitsPerPage);
        const totalColumns = totalPages * bitsPerPage;

        // 限制最大网格数，避免崩溃
        const maxColumns = 3000; // 最多显示500格（约31页）
        const displayColumns = Math.min(totalColumns, maxColumns);

        // 清空网格
        grid.innerHTML = '';
        grid.style.gridTemplateColumns = `60px repeat(${displayColumns}, 40px)`;

        // 使用 DocumentFragment 批量创建元素
        const fragment = document.createDocumentFragment();

        // 创建表头
        const headerCell = document.createElement('div');
        headerCell.className = 'grid-header';
        headerCell.textContent = '轨道';
        fragment.appendChild(headerCell);

        for (let i = 0; i < displayColumns; i++) {
            const isBeat = i % 4 === 0;
            const isPageStart = i % bitsPerPage === 0;
            const pageNum = Math.floor(i / bitsPerPage) + 1;
            const bitInPage = i % bitsPerPage;

            const header = document.createElement('div');
            header.className = `grid-header ${isBeat ? 'beat-marker' : ''} ${isPageStart ? 'page-start' : ''}`;
            header.title = `页${pageNum} - 格${bitInPage}`;
            header.textContent = bitInPage;
            fragment.appendChild(header);
        }

        // 创建音符行
        const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        for (let i = keys; i >= 1; i--) {
            const midiNote = 48 + (i - 1);
            const noteName = noteNames[(midiNote) % 12] + Math.floor(midiNote / 12 - 1);

            const rowLabel = document.createElement('div');
            rowLabel.className = 'grid-row';
            rowLabel.title = `MIDI ${midiNote}`;
            rowLabel.innerHTML = `${noteName}<br>1Key${i}`;
            fragment.appendChild(rowLabel);

            for (let j = 0; j < displayColumns; j++) {
                const isBeat = j % 4 === 0;
                const isPageStart = j % bitsPerPage === 0;

                const cell = document.createElement('div');
                cell.className = `grid-cell ${isBeat ? 'beat-marker' : ''} ${isPageStart ? 'page-start' : ''}`;
                cell.dataset.key = i;
                cell.dataset.time = j;
                fragment.appendChild(cell);
            }
        }

        // 一次性添加到DOM
        grid.appendChild(fragment);

        // 填充音符（使用缓存的选择器）
        const cellMap = new Map();
        this.convertedData.songNotes.forEach(note => {
            const keyMatch = note.key.match(/1Key(\d+)/);
            if (!keyMatch) return;

            const keyNumber = parseInt(keyMatch[1])+1;
            const bitPosition = Math.floor(note.time / msPerBit);

            // 超出显示范围的音符不处理
            if (bitPosition >= displayColumns) return;

            const cellKey = `${keyNumber}-${bitPosition}`;
            let cell = cellMap.get(cellKey);

            if (!cell) {
                cell = grid.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
                if (cell) {
                    cellMap.set(cellKey, cell);
                }
            }

            if (cell) {
                cell.classList.add('has-note');
                const pageNum = Math.floor(bitPosition / bitsPerPage) + 1;
                const bitInPage = bitPosition % bitsPerPage;
                cell.title = `${note.key} @ ${note.time}ms\n页${pageNum} 格${bitInPage}`;
            }
        });

        // 显示统计信息
        const statsInfo = `网格信息: 总时长=${(totalDuration / 1000).toFixed(1)}秒, 显示=${displayColumns}格/${totalColumns}格, 总页数=${totalPages}`;
        console.log(statsInfo);

        if (displayColumns < totalColumns) {
            alert(`注意：歌曲过长，网格已限制为${displayColumns}格（约${Math.floor(displayColumns / 16)}页）以避免性能问题。\n完整长度需要${totalColumns}格。`);
        }
    }

    // play() {
    //     if (!this.convertedData || this.isPlaying) return;

    //     this.isPlaying = true;
    //     document.getElementById('playBtn').disabled = true;
    //     document.getElementById('stopBtn').disabled = false;
    //     document.getElementById('progressBar').style.display = 'block';

    //     const totalDuration = this.convertedData.songNotes.length > 0
    //         ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
    //         : 0;

    //     const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
    //     const bitsPerPage = 16;

    //     const gridContainer = document.querySelector('.grid-container');
    //     const cursor = document.getElementById('playbackCursor');
    //     const grid = document.getElementById('grid');

    //     // 显示进度线
    //     cursor.style.display = 'block';

    //     // 获取网格信息
    //     const gridRect = grid.getBoundingClientRect();
    //     const containerRect = gridContainer.getBoundingClientRect();
    //     const cellWidth = 40; // 单元格宽度
    //     const labelWidth = 60; // 左侧标签宽度

    //     const totalBits = Math.ceil(totalDuration / msPerBit);
    //     const containerWidth = containerRect.width;
    //     const gridWidth = labelWidth + totalBits * cellWidth;

    //     // 播放开始时间
    //     const startTime = Date.now();
    //     const playbackSpeedFactor = this.playbackSpeed;

    //     // 用于跟踪已播放的音符
    //     const playedNotes = new Set();

    //     // 动画循环更新进度线位置
    //     const updateCursor = () => {
    //         if (!this.isPlaying) return;

    //         const elapsed = (Date.now() - startTime) * playbackSpeedFactor;
    //         const currentBit = elapsed / msPerBit;

    //         // 计算进度线位置
    //         let cursorX = labelWidth + currentBit * cellWidth;

    //         // 计算滚动逻辑
    //         if (currentBit <= bitsPerPage / 2) {
    //             // 开始阶段：进度线从左边界移动
    //             gridContainer.scrollLeft = 0;
    //         } else if (currentBit >= totalBits - bitsPerPage / 2) {
    //             // 结束阶段：进度线移动到右边界
    //             gridContainer.scrollLeft = gridWidth - containerWidth;
    //         } else {
    //             // 中间阶段：进度线固定在容器中心，滚动网格
    //             const centerOffset = containerWidth / 2;
    //             gridContainer.scrollLeft = cursorX - centerOffset;
    //             cursorX = centerOffset + gridContainer.scrollLeft;
    //         }

    //         cursor.style.left = `${cursorX}px`;

    //         // 更新进度条
    //         const progress = Math.min((elapsed / totalDuration) * 100, 100);
    //         document.getElementById('progressFill').style.width = `${progress}%`;

    //         // 继续动画
    //         if (elapsed < totalDuration + 500) {
    //             this.cursorAnimationFrame = requestAnimationFrame(updateCursor);
    //         }
    //     };

    //     // 启动进度线动画
    //     this.cursorAnimationFrame = requestAnimationFrame(updateCursor);

    //     // 播放音符
    //     this.convertedData.songNotes.forEach((note, index) => {
    //         const delay = note.time / playbackSpeedFactor;

    //         const timeout = setTimeout(() => {
    //             // 播放音符声音
    //             this.player.queueWaveTable(
    //                 this.audioContext,
    //                 this.audioContext.destination,
    //                 this.instrument,
    //                 this.audioContext.currentTime,
    //                 note.midi,
    //                 0.5,
    //                 0.7
    //             );

    //             // 高亮显示音符
    //             const keyMatch = note.key.match(/1Key(\d+)/);
    //             if (keyMatch) {
    //                 const keyNumber = parseInt(keyMatch[1]);
    //                 const bitPosition = Math.floor(note.time / msPerBit);

    //                 const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
    //                 if (cell && !playedNotes.has(`${keyNumber}-${bitPosition}`)) {
    //                     cell.classList.add('playing');
    //                     playedNotes.add(`${keyNumber}-${bitPosition}`);

    //                     // 500ms后移除高亮
    //                     setTimeout(() => {
    //                         cell.classList.remove('playing');
    //                     }, 500);
    //                 }
    //             }
    //         }, delay);

    //         this.playTimeouts.push(timeout);
    //     });

    //     // 播放结束
    //     const endTimeout = setTimeout(() => {
    //         this.stop();
    //     }, totalDuration / playbackSpeedFactor + 1000);

    //     this.playTimeouts.push(endTimeout);
    // }

    play() {
        if (!this.convertedData || this.isPlaying) return;

        this.isPlaying = true;
        document.getElementById('playBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('progressBar').style.display = 'block';

        const totalDuration = this.convertedData.songNotes.length > 0
            ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
            : 0;

        const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
        const bitsPerPage = 16;

        const gridContainer = document.querySelector('.grid-container');
        const cursor = document.getElementById('playbackCursor');
        const grid = document.getElementById('grid');

        // 显示进度线
        cursor.style.display = 'block';

        // 获取网格信息
        const gridRect = grid.getBoundingClientRect();
        const containerRect = gridContainer.getBoundingClientRect();
        const cellWidth = 40; // 单元格宽度
        const labelWidth = 60; // 左侧标签宽度

        const totalBits = Math.ceil(totalDuration / msPerBit);
        const containerWidth = containerRect.width;
        const gridWidth = labelWidth + totalBits * cellWidth;

        // 播放开始时间
        const startTime = Date.now();
        const playbackSpeedFactor = this.playbackSpeed;

        // 用于跟踪已播放的音符
        const playedNotes = new Set();

        // 动画循环更新进度线位置
        const updateCursor = () => {
            if (!this.isPlaying) return;

            const elapsed = (Date.now() - startTime) * playbackSpeedFactor;
            const currentBit = elapsed / msPerBit;

            // 计算进度线位置
            let cursorX = labelWidth + currentBit * cellWidth;

            // 加快网格滚动速度：确保进度线与音符同步
            if (currentBit < bitsPerPage) {
                gridContainer.scrollLeft = 0; // 初始阶段，进度线快速移动
            } else if (currentBit >= totalBits - bitsPerPage / 2) {
                gridContainer.scrollLeft = gridWidth - containerWidth; // 最后阶段，进度线快速移动
            } else {
                // 中间部分：进度线固定在容器中间，滚动网格
                const centerOffset = containerWidth / 2;
                gridContainer.scrollLeft = cursorX - centerOffset;
                cursorX = centerOffset + gridContainer.scrollLeft;
            }

            cursor.style.left = `${cursorX}px`;

            // 更新进度条
            const progress = Math.min((elapsed / totalDuration) * 100, 100);
            document.getElementById('progressFill').style.width = `${progress}%`;

            // 继续动画
            if (elapsed < totalDuration + 500) {
                this.cursorAnimationFrame = requestAnimationFrame(updateCursor);
            }
        };

        // 启动进度线动画
        this.cursorAnimationFrame = requestAnimationFrame(updateCursor);

        // 播放音符并同步
        this.convertedData.songNotes.forEach((note, index) => {
            const delay = note.time / playbackSpeedFactor;

            const timeout = setTimeout(() => {
                // 播放音符声音
                this.player.queueWaveTable(
                    this.audioContext,
                    this.audioContext.destination,
                    this.instrument,
                    this.audioContext.currentTime,
                    note.midi,
                    0.5,
                    0.7
                );

                // 高亮显示音符
                const keyMatch = note.key.match(/1Key(\d+)/);
                if (keyMatch) {
                    const keyNumber = parseInt(keyMatch[1]);
                    const bitPosition = Math.floor(note.time / msPerBit);

                    const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
                    if (cell && !playedNotes.has(`${keyNumber}-${bitPosition}`)) {
                        cell.classList.add('playing');
                        playedNotes.add(`${keyNumber}-${bitPosition}`);

                        // 500ms后移除高亮
                        setTimeout(() => {
                            cell.classList.remove('playing');
                        }, 500);
                    }
                }
            }, delay);

            this.playTimeouts.push(timeout);
        });

        // 播放结束
        const endTimeout = setTimeout(() => {
            this.stop();
        }, totalDuration / playbackSpeedFactor + 1000);

        this.playTimeouts.push(endTimeout);
    }

    // play() {
    //     if (!this.convertedData || this.isPlaying) return;

    //     this.isPlaying = true;
    //     document.getElementById('playBtn').disabled = true;
    //     document.getElementById('stopBtn').disabled = false;
    //     document.getElementById('progressBar').style.display = 'block';

    //     const totalDuration = this.convertedData.songNotes.length > 0
    //         ? this.convertedData.songNotes[this.convertedData.songNotes.length - 1].time
    //         : 0;

    //     const msPerBit = (60000 / this.convertedData.bpm) * 4 / 16;
    //     const bitsPerPage = 16;

    //     const gridContainer = document.querySelector('.grid-container');
    //     const cursor = document.getElementById('playbackCursor');
    //     const grid = document.getElementById('grid');

    //     // 显示进度线
    //     cursor.style.display = 'block';

    //     // 获取网格信息
    //     const gridRect = grid.getBoundingClientRect();
    //     const containerRect = gridContainer.getBoundingClientRect();
    //     const cellWidth = 40; // 单元格宽度
    //     const labelWidth = 60; // 左侧标签宽度

    //     const totalBits = Math.ceil(totalDuration / msPerBit);
    //     const containerWidth = containerRect.width;
    //     const gridWidth = labelWidth + totalBits * cellWidth;

    //     // 播放开始时间
    //     const startTime = Date.now();
    //     const playbackSpeedFactor = this.playbackSpeed;

    //     // 用于跟踪已播放的音符
    //     const playedNotes = new Set();

    //     // 动画循环更新进度线位置
    //     const updateCursor = () => {
    //         if (!this.isPlaying) return;

    //         const elapsed = (Date.now() - startTime) * playbackSpeedFactor;
    //         const currentBit = elapsed / msPerBit;

    //         // 计算进度线位置（前16格平滑过渡）
    //         let cursorX = labelWidth + currentBit * cellWidth;

    //         // 在前16格内，进度线逐步从左边开始平滑过渡
    //         if (currentBit < bitsPerPage) {
    //             // 前16格内，逐渐加速滚动
    //             gridContainer.scrollLeft = 0;
    //         } else if (currentBit >= totalBits - bitsPerPage / 2) {
    //             // 结束阶段：进度线移动到右边界
    //             gridContainer.scrollLeft = gridWidth - containerWidth;
    //         } else {
    //             // 中间阶段：进度线固定在容器中心，滚动网格
    //             const centerOffset = containerWidth / 2;
    //             gridContainer.scrollLeft = cursorX - centerOffset;
    //             cursorX = centerOffset + gridContainer.scrollLeft;
    //         }

    //         cursor.style.left = `${cursorX}px`;

    //         // 更新进度条
    //         const progress = Math.min((elapsed / totalDuration) * 100, 100);
    //         document.getElementById('progressFill').style.width = `${progress}%`;

    //         // 继续动画
    //         if (elapsed < totalDuration + 500) {
    //             this.cursorAnimationFrame = requestAnimationFrame(updateCursor);
    //         }
    //     };

    //     // 启动进度线动画
    //     this.cursorAnimationFrame = requestAnimationFrame(updateCursor);

    //     // 播放音符
    //     this.convertedData.songNotes.forEach((note, index) => {
    //         const delay = note.time / playbackSpeedFactor;

    //         const timeout = setTimeout(() => {
    //             // 播放音符声音
    //             this.player.queueWaveTable(
    //                 this.audioContext,
    //                 this.audioContext.destination,
    //                 this.instrument,
    //                 this.audioContext.currentTime,
    //                 note.midi,
    //                 0.5,
    //                 0.7
    //             );

    //             // 高亮显示音符
    //             const keyMatch = note.key.match(/1Key(\d+)/);
    //             if (keyMatch) {
    //                 const keyNumber = parseInt(keyMatch[1]);
    //                 const bitPosition = Math.floor(note.time / msPerBit);

    //                 const cell = document.querySelector(`[data-key="${keyNumber}"][data-time="${bitPosition}"]`);
    //                 if (cell && !playedNotes.has(`${keyNumber}-${bitPosition}`)) {
    //                     cell.classList.add('playing');
    //                     playedNotes.add(`${keyNumber}-${bitPosition}`);

    //                     // 500ms后移除高亮
    //                     setTimeout(() => {
    //                         cell.classList.remove('playing');
    //                     }, 500);
    //                 }
    //             }
    //         }, delay);

    //         this.playTimeouts.push(timeout);
    //     });

    //     // 播放结束
    //     const endTimeout = setTimeout(() => {
    //         this.stop();
    //     }, totalDuration / playbackSpeedFactor + 1000);

    //     this.playTimeouts.push(endTimeout);
    // }

    stop() {
        // 取消所有定时器
        this.playTimeouts.forEach(timeout => clearTimeout(timeout));
        this.playTimeouts = [];

        // 取消进度线动画
        if (this.cursorAnimationFrame) {
            cancelAnimationFrame(this.cursorAnimationFrame);
            this.cursorAnimationFrame = null;
        }

        // 停止音频
        this.player.cancelQueue(this.audioContext);

        // 隐藏进度线
        const cursor = document.getElementById('playbackCursor');
        if (cursor) {
            cursor.style.display = 'none';
        }

        // 移除所有高亮
        document.querySelectorAll('.grid-cell.playing').forEach(cell => {
            cell.classList.remove('playing');
        });

        this.isPlaying = false;
        document.getElementById('playBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        document.getElementById('progressFill').style.width = '0%';

        // 重置滚动位置
        document.querySelector('.grid-container').scrollLeft = 0;
    }

    // stop() {
    //     this.playTimeouts.forEach(timeout => clearTimeout(timeout));
    //     this.playTimeouts = [];
    //     this.player.cancelQueue(this.audioContext);

    //     document.querySelectorAll('.grid-cell.active').forEach(cell => {
    //         cell.classList.remove('active');
    //     });

    //     this.isPlaying = false;
    //     document.getElementById('playBtn').disabled = false;
    //     document.getElementById('stopBtn').disabled = true;
    //     document.getElementById('progressFill').style.width = '0%';
    // }


    download() {
        if (!this.convertedData) return;

        const exportData = [{
            ...this.convertedData,
            songNotes: this.convertedData.songNotes.map(note => ({
                time: note.time,
                key: note.key
            }))
        }];

        // 生成紧凑的 JSON（无空格和换行）
        const jsonString = JSON.stringify(exportData);

        // 将字符串转换为 UTF-16LE 编码
        const utf16leData = this.encodeUTF16LE(jsonString);

        // 创建 Blob
        const blob = new Blob([utf16leData], { type: 'application/json;charset=utf-16le' });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'converted-music.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // UTF-16LE 编码函数
    encodeUTF16LE(str) {
        const buf = new ArrayBuffer(str.length * 2);
        const bufView = new Uint16Array(buf);

        for (let i = 0; i < str.length; i++) {
            bufView[i] = str.charCodeAt(i);
        }

        return new Uint8Array(buf);
    }


}

window.addEventListener('DOMContentLoaded', () => {
    new MIDIConverter();
});
