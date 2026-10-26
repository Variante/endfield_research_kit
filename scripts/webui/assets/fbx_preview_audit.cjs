/* Exercise the actual browser FBX decoder without WebGL or browser state.
 * This checks static mesh/skin/LOD construction, not rendered appearance.
 * Selection: [{path, sha256, expectedGeometryInstances?}], generated locally.
 */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function decoder(source) {
  const section = (start, end) => {
    const at = source.indexOf(start), until = source.indexOf(end, at);
    if (at < 0 || until <= at) throw new Error(`Frontend decoder boundary changed: ${start}`);
    return source.slice(at, until);
  };
  const context = vm.createContext({TextDecoder, Blob, Response, DecompressionStream});
  vm.runInContext(section('  function finalizeMesh(', '  async function loadFbxAsset(')
    + section('  function parseBinaryFbxTree(', '  function cleanFbxSampleName(')
    + section('  function modelObjectShown(', '  // Software fallback'), context);
  return context;
}

async function audit(selection, source) {
  const api = decoder(source), rows = [];
  for (const item of selection) {
    const row = {path: item.path};
    try {
      const data = fs.readFileSync(item.path);
      row.sha256 = crypto.createHash('sha256').update(data).digest('hex');
      if (!item.sha256 || row.sha256 !== item.sha256) throw new Error('Selected FBX hash differs');
      const buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
      const tree = api.parseBinaryFbxTree(buffer);
      if (!tree.complete) throw new Error('Frontend tree parser is incomplete');
      const model = await api.buildFbxMesh(tree, buffer);
      if (!model || !model.indices?.length || !model.positions?.length) throw new Error('No preview triangles');
      if (item.expectedGeometryInstances !== undefined && model.objects.length !== item.expectedGeometryInstances)
        throw new Error(`Preview object count differs: expected=${item.expectedGeometryInstances}; actual=${model.objects.length}`);
      for (const values of [model.positions, model.normals, model.center, [model.scale, model.fitRadius]])
        if (!Array.from(values).every(Number.isFinite)) throw new Error('Non-finite preview geometry');
      const visible = model.objects.filter(object => api.modelObjectShown(model, object));
      if (!visible.length) throw new Error('Default selection hides every part');
      Object.assign(row, {status:'validated', objects:model.objects.length, triangles:model.indices.length/3,
        defaultLod:model.lod, visibleParts:visible.length, fitRadius:model.fitRadius});
    } catch (error) { row.status='failed'; row.error=error.message; }
    rows.push(row);
    if (rows.length % 100 === 0) process.stdout.write(`FBX previews checked: ${rows.length}/${selection.length}\n`);
  }
  return {schema:'endfield.fbx-preview-audit.v1', frontendSha256:crypto.createHash('sha256').update(source).digest('hex'),
    checked:rows.length, failed:rows.filter(row => row.status !== 'validated').length, rows,
    evidenceBoundary:'Stored static FBX mesh, skin and default LOD construction in the current frontend. No material/GPU appearance or runtime visibility claim.'};
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 4 || args[0] !== '--selection' || args[2] !== '--report')
    throw new Error('Usage: node scripts/webui/assets/fbx_preview_audit.cjs --selection JSON --report REPORT');
  const source = fs.readFileSync(path.resolve(__dirname, '../../../webui/assets.js'), 'utf8');
  const result = await audit(JSON.parse(fs.readFileSync(args[1], 'utf8')), source);
  fs.mkdirSync(path.dirname(args[3]), {recursive:true});
  fs.writeFileSync(args[3], JSON.stringify(result, null, 2));
  process.stdout.write(`FBX preview audit: checked=${result.checked}; failed=${result.failed}\n`);
  if (result.failed) process.exitCode=1;
}

module.exports = {decoder, audit};
if (require.main === module) main().catch(error => {console.error(error);process.exitCode=1;});
