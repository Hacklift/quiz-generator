// Review-only migration of fragmented JSX copy into whole translatable messages.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import ts from 'typescript';
const messages=JSON.parse(fs.readFileSync('src/features/locale/messages/ui.en.json','utf8'));
const changes={};
function* files(dir){for(const d of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,d.name);if(d.isDirectory())yield*files(p);else if(p.endsWith('.tsx'))yield p;}}
const walk=(n,f)=>{f(n);ts.forEachChild(n,c=>walk(c,f));};
for(const file of [...files('src'),...files('pages')]){
 if(process.argv[2]&&file!==process.argv[2])continue;
 const old=fs.readFileSync(file,'utf8');const ast=ts.createSourceFile(file,old,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const edits=[];
 walk(ast,n=>{
  if(!ts.isJsxElement(n))return;
  const pieces=[];const values=[];let sourceCount=0,invalid=false;
  for(const c of n.children){
   if(ts.isJsxText(c)){if(c.text.trim())pieces.push(c.text.trim());continue;}
   if(!ts.isJsxExpression(c)||!c.expression){invalid=true;break;}
   const e=c.expression;let hasMarkup=false;
   walk(e,x=>{if(ts.isJsxElement(x)||ts.isJsxSelfClosingElement(x)||ts.isJsxFragment(x)||ts.isArrowFunction(x))hasMarkup=true;});
   if(hasMarkup){invalid=true;break;}
   if(ts.isStringLiteral(e)){if(e.text.trim())pieces.push(e.text.trim());continue;}
   if(ts.isCallExpression(e)&&e.expression.getText(ast)==='uiText'&&e.arguments.length===1&&ts.isStringLiteral(e.arguments[0])){
    const source=messages[e.arguments[0].text];if(!source){invalid=true;break;}pieces.push(source);sourceCount++;continue;
   }
   pieces.push('{{value'+values.length+'}}');values.push(e.getText(ast));
  }
  if(invalid||sourceCount===0||pieces.length<2||!values.length)return;
  const source=pieces.join(' ').replace(/\s+([.,:;!?%\)\]])/g,'$1').replace(/([\(\[])\s+/g,'$1').replace(/ \/ /g,'/');
  const id='m'+crypto.createHash('sha256').update(source).digest('hex').slice(0,16);messages[id]=source;
  const replacement='{uiText('+JSON.stringify(id)+', { '+values.map((v,i)=>'value'+i+': '+v).join(', ')+' })}';
  edits.push({start:n.openingElement.end,end:n.closingElement.getStart(ast),text:replacement});
 });
 let content=old;for(const e of edits.sort((a,b)=>b.start-a.start))content=content.slice(0,e.start)+e.text+content.slice(e.end);
 if(content!==old)changes[file]={old,content};
}
console.log(JSON.stringify(process.argv[2]?changes[process.argv[2]]:{files:Object.keys(changes),messages}));
