// Review-only AST migration: output patches; never modifies files itself.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import ts from 'typescript';
const messages = JSON.parse(fs.readFileSync('src/features/locale/messages/ui.en.json', 'utf8'));
const changes = {};
const props = new Set(['label','title','description','subtitle','heading','copy','quote','who','cta','microlabel','unit','emptyMessage','loadingText','placeholder','aria-label','alt','helperText','successMessage']);
const isText = s => /[a-zA-Z]{2}/.test(s) && !/^(https?:|\/[^ ]|#|@)/.test(s);
const walk = (n, f) => { f(n); ts.forEachChild(n, c => walk(c,f)); };
const owner = n => { for(let p=n.parent;p;p=p.parent) if(ts.isFunctionDeclaration(p)||ts.isArrowFunction(p)||ts.isFunctionExpression(p)) {
  const name=p.name?.text||(ts.isVariableDeclaration(p.parent)?p.parent.name.getText(): '');
  if(/^[A-Z]/.test(name)&&p.body) return p;
} return null; };
function* files(dir) { for(const d of fs.readdirSync(dir,{withFileTypes:true})) { const p=path.join(dir,d.name); if(d.isDirectory())yield*files(p);else if(/\.tsx$/.test(p))yield p; } }
const apply = (s, edits) => { for(const e of edits.sort((a,b)=>b.start-a.start))s=s.slice(0,e.start)+e.text+s.slice(e.end); return s; };
for(const file of [...files('src'),...files('pages')]) {
 if(process.argv[2] && file!==process.argv[2])continue;
 if(file.includes('features/locale/'))continue;
 const old=fs.readFileSync(file,'utf8'); let content=old;
 let ast=ts.createSourceFile(file,content,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const repair=[];
 walk(ast,n=>{
   if(!ts.isCallExpression(n)||n.expression.getText(ast)!=='uiText'||!ts.isStringLiteral(n.arguments[0]))return;
   const p=n.parent;
   if(ts.isBinaryExpression(p)&&['===','!==','==','!='].includes(p.operatorToken.getText(ast))) {
     repair.push({start:n.getStart(ast),end:n.end,text:JSON.stringify(messages[n.arguments[0].text])});
   }
 });
 content=apply(content,repair);
 ast=ts.createSourceFile(file,content,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 // Move private static display data into its sole consuming component, so it
 // can use that component's translator and updates immediately on switching.
 const moves=[];
 for(const statement of ast.statements) {
   if(!ts.isVariableStatement(statement)||statement.modifiers?.length||statement.declarationList.declarations.length!==1)continue;
   const d=statement.declarationList.declarations[0];
   if(!ts.isIdentifier(d.name)||!d.initializer||(!ts.isArrayLiteralExpression(d.initializer)&&!ts.isObjectLiteralExpression(d.initializer)))continue;
   let display=false;
   walk(d.initializer,n=>{if(ts.isPropertyAssignment(n)&&props.has(n.name.getText(ast).replaceAll('"','')))display=true;});
   if(!display)continue;
   const owners=new Set();let outside=false;
   walk(ast,n=>{if(ts.isIdentifier(n)&&n.text===d.name.text&&n!==d.name){const o=owner(n);if(!o)outside=true;else owners.add(o);}});
   const fn=[...owners][0];
   if(outside||owners.size!==1||!ts.isBlock(fn.body))continue;
   moves.push({start:statement.getStart(ast),end:statement.end,text:''});
   moves.push({start:fn.body.getStart(ast)+1,end:fn.body.getStart(ast)+1,text:'\n'+statement.getText(ast)+'\n'});
 }
 content=apply(content,moves);
 ast=ts.createSourceFile(file,content,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const edits=[];const owners=new Set();
 function add(n,text,opts='') {
   const o=owner(n);if(!o||!isText(text))return;
   const id='m'+crypto.createHash('sha256').update(text).digest('hex').slice(0,16);messages[id]=text;
   edits.push({start:n.getStart(ast),end:n.end,text:'uiText('+JSON.stringify(id)+opts+')'});owners.add(o);
 }
 walk(ast,n=>{
   if(!ts.isStringLiteral(n)&&!ts.isNoSubstitutionTemplateLiteral(n)&&!ts.isTemplateExpression(n))return;
   const p=n.parent;
   let display=ts.isPropertyAssignment(p)&&props.has(p.name.getText(ast).replaceAll('"',''));
   let ancestor=p;
   while(ancestor&&(ts.isConditionalExpression(ancestor)||ts.isParenthesizedExpression(ancestor)||
     (ts.isBinaryExpression(ancestor)&&['||','??'].includes(ancestor.operatorToken.getText(ast)))))ancestor=ancestor.parent;
   if(ancestor&&ts.isJsxExpression(ancestor)&&(!ts.isJsxAttribute(ancestor.parent)||props.has(ancestor.parent.name.text)))display=true;
   if(ancestor&&ts.isCallExpression(ancestor)&&/^(setError|setSaveError|setBillingError|setErrorMessage|toast\.(success|error|loading))$/.test(ancestor.expression.getText(ast)))display=true;
   if(ts.isArrayLiteralExpression(p)&&ts.isPropertyAssignment(p.parent)&&['features','benefits'].includes(p.parent.name.getText(ast)))display=true;
   if(ts.isJsxExpression(p)&&ts.isJsxAttribute(p.parent)&&props.has(p.parent.name.text))display=true;
   if(ts.isCallExpression(p)&&/^(setError|setSaveError|setBillingError|setErrorMessage|toast\.(success|error|loading))$/.test(p.expression.getText(ast)))display=true;
   if(!display)return;
   if(ts.isTemplateExpression(n)) {
     let text=n.head.text;const values=[];
     for(const [i,s]of n.templateSpans.entries()){text+='{{value'+i+'}}'+s.literal.text;values.push('value'+i+': '+s.expression.getText(ast));}
     add(n,text,', { '+values.join(', ')+' }');
   } else add(n,n.text);
 });
 for(const fn of owners) {
   if(ts.isBlock(fn.body)) {
     const existing=fn.body.statements.find(s=>ts.isVariableStatement(s)&&s.getText(ast).includes('useTranslation("ui")'));
     if(existing)edits.push({start:existing.getStart(ast),end:existing.end,text:''});
   }
   if(ts.isBlock(fn.body))edits.push({start:fn.body.getStart(ast)+1,end:fn.body.getStart(ast)+1,text:'\nconst { t: uiText } = useTranslation("ui");\n'});
 }
 content=apply(content,edits);
 if(owners.size&&!/import\s*\{[^}]*\buseTranslation\b[^}]*\}\s*from\s*["']react-i18next["']/.test(content)) {
   const pos=content.startsWith('"use client";')?'"use client";'.length:0;
   content=content.slice(0,pos)+'\nimport { useTranslation } from "react-i18next";\n'+content.slice(pos);
 }
 if(content!==old)changes[file]={old,content};
}
console.log(JSON.stringify(process.argv[2] ? changes[process.argv[2]] : {files:Object.keys(changes),messages}));
