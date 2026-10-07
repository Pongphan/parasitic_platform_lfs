// Node-only contract test for the reused iframe, with a minimal DOM/canvas stub.
// This checks event behavior; it is not a rendered-browser visual test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname,'../component_layout/viewer_component/index.html'),'utf8');
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const messages = [], elements = {}, windowEvents = {};
const drawContext = new Proxy({}, {get:(obj,key)=>obj[key] || (()=>{}),set:(obj,key,value)=>(obj[key]=value,true)});
function element(id) {
  return elements[id] ||= {style:{},events:{},textContent:'',width:0,height:0,
    addEventListener(type,fn){this.events[type]=fn},
    getContext(){return drawContext},getBoundingClientRect(){return {left:0,top:0}},
    focus(){document.activeElement=this},setPointerCapture(){}};
}
const document = {documentElement:{clientWidth:640,dataset:{}},activeElement:null,
  getElementById:element,querySelector:element};
const parent = {postMessage(msg){messages.push(msg)}};
const window = {parent,innerWidth:640,addEventListener(type,fn){windowEvents[type]=fn},clearTimeout(){},setTimeout(fn){fn()}};
class Image {constructor(){this.complete=true;this.naturalWidth=1200;this.naturalHeight=900;}}
vm.runInNewContext(code,{document,window,Image,console,Math,Date,Number,String,
  getComputedStyle(){return {getPropertyValue(){return ''}}}, requestAnimationFrame(){}});
assert.equal(messages[0].type,'streamlit:componentReady');
const render = {source:parent,data:{type:'streamlit:render',args:{viewport:0,init_zoom:1,init_panX:0,init_panY:0,image_b64:'test',image_id:'sample-1',theme_mode:'Light'}}};
windowEvents.message(render);
assert.equal(elements.cv.width,636);
assert.equal(document.documentElement.dataset.theme,'light');
const values=()=>messages.filter(m=>m.type==='streamlit:setComponentValue');
elements.zoomInBtn.events.click();
elements.cv.events.pointerdown({clientX:100,clientY:100,pointerId:1});
elements.cv.events.pointermove({clientX:120,clientY:110});
elements.cv.events.pointerup();
assert.equal(values().length,0,'Pan and zoom must not trigger Python inference');
assert.match(elements.selectionStatus.textContent,/Selection changed/);
elements.calcBtn.events.click();
let result=values().at(-1).value;
assert.equal(result.action,'calculate');
assert.equal(result.image_id,'sample-1');
assert.equal(result.zoom,1.1);
assert.equal(result.panX,20);
assert.equal(result.panY,10);
assert.equal(result.viewport,636);
assert.ok(result.calc_token);
// The point under the ROI center must stay fixed even with an off-center cursor.
const beforeWheel = result;
elements.cv.events.wheel({preventDefault(){},clientX:20,clientY:40,deltaY:-1});
assert.equal(values().length,1);
elements.calcBtn.events.click();
result=values().at(-1).value;
assert.ok(result.zoom>1.1);
assert.ok(Math.abs(result.panX/result.zoom-beforeWheel.panX/beforeWheel.zoom)<1e-9);
assert.ok(Math.abs(result.panY/result.zoom-beforeWheel.panY/beforeWheel.zoom)<1e-9);
assert.notEqual(values()[0].value.calc_token,result.calc_token);
windowEvents.message({source:{},data:{type:'streamlit:render',args:{image_id:'foreign'}}});
elements.calcBtn.events.click();
assert.equal(values().at(-1).value.image_id,'sample-1','Ignore messages from non-parent windows');
const beforePad = values().at(-1).value;
const valueCount = values().length;
elements.panLeftBtn.events.click();
elements.calcBtn.events.click();
assert.ok(values().at(-1).value.panX > beforePad.panX);
elements.panRightBtn.events.click();
elements.panUpBtn.events.click();
elements.calcBtn.events.click();
assert.ok(Math.abs(values().at(-1).value.panX-beforePad.panX)<1e-9);
assert.ok(values().at(-1).value.panY > beforePad.panY);
elements.panDownBtn.events.click();
elements.zoomOutBtn.events.click();
assert.equal(values().length,valueCount+2,'Touch controls wait for Calculate');
elements.calcBtn.events.click();
assert.ok(values().at(-1).value.zoom < beforePad.zoom);
const beforeFit = values().length;
elements.fitBtn.events.click();
assert.equal(values().length,beforeFit,'Fit image must not trigger inference');
assert.equal(elements.zoomReadout.textContent,'100%');
assert.match(elements.selectionStatus.textContent,/Selection changed/);
elements.calcBtn.events.click();
assert.equal(values().at(-1).value.zoom,1);
assert.equal(values().at(-1).value.panX,0);
assert.equal(values().at(-1).value.panY,0);
// A narrow viewport puts controls below the canvas; the iframe must contain them.
document.documentElement.clientWidth=340;
elements['.wrap'].scrollHeight=620;
const beforeResize=values().length;
windowEvents.resize();
assert.equal(elements.cv.width,336);
assert.equal(messages.filter(m=>m.type==='streamlit:setFrameHeight').at(-1).height,628);
assert.equal(values().length,beforeResize,'Responsive layout must not trigger inference');
const css=fs.readFileSync(path.join(__dirname,'../component_layout/viewer_component/viewer.css'),'utf8');
assert.match(css,/--grid-line:#ADD8E6/);
assert.match(css,/--center-line:#2563EB/);
assert.match(css,/:root\[data-theme="dark"\][\s\S]*--grid-line:#ADD8E6/);
assert.match(html,/const PAN_STEP_RATIO = 0\.06/);
assert.match(html,/const ZOOM_IN_FACTOR = 1\.10/);
console.log('Viewer contract passed: initialize, responsive height, drag, zoom, fit image, analyze, source binding, no movement reruns.');
