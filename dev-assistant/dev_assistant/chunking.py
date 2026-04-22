import re
from typing import Any, List, Sequence
from xml.dom.expatbuilder import TEXT_NODE
from llama_index.core.node_parser.interface import NodeParser
from llama_index.core.schema import BaseNode, Document, NodeRelationship, TextNode
from llama_index.core.callbacks.base import CallbackManager
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.utils import get_tqdm_iterable
from llama_index.core.node_parser.node_utils import default_id_func
from llama_index.core.bridge.pydantic import Field
from llama_index.core.node_parser import SentenceSplitter, CodeSplitter

from tree_sitter import Node
from dataclasses import dataclass
import pathlib
from typing import Any, List
import tree_sitter_language_pack
from collections import deque

LANGUAGES = {
    'cs': 'csharp',
    'ts': 'typescript',
    'js': 'javascript',
    'py': 'python',
    'go': 'go',
    'java': 'java',
}

FUNCTION_BLOCK_NODE_TYPES = [
    "block", "statement_block", "arrow_expression_clause"
]

FUNCTION_DECLARATION_NODE_TYPES = [
    "method_definition",
    "function_definition",
    "function_item",
    "function_declaration",
    "method_declaration",
    "constructor_declaration",
    "operator_declaration",
]


def get_lang_for_file(file_name: str):
    ext = pathlib.Path(file_name).suffix.strip('.')
    if ext in LANGUAGES:
        return LANGUAGES[ext]
    return None

def get_parser_for_file(file_name: str):
    lang = get_lang_for_file(file_name)
    if lang:
        return tree_sitter_language_pack.get_parser(lang)
    return None


def replace_collapse(node: Node):
    if node.type == 'arrow_expression_clause':
        return "=> ...;".encode('utf-8')
    return "{ ... }".encode('utf-8')


def first_child(node: Node, grammarName: List[str] | str):
    if isinstance(grammarName, str):
        grammarName = [grammarName]
    return next((child for child in node.children if child.type in grammarName), None)


def replace_children(
        node: Node, code: bytes, blockTypes: List[str], collapseTypes: List[str],
        collapseBlockTypes: List[str], maxChunkSize: int
):
    code = code[:node.end_byte]
    block = first_child(node, blockTypes)
    collapsedChildren = deque()
    if block:
        childrenToCollapse = [child for child in block.children if child.type in collapseTypes]
        for child in reversed(childrenToCollapse):
            grandChild = first_child(child, collapseBlockTypes)
            if grandChild:
                start = grandChild.start_byte
                end = child.end_byte
                collapsedChild = code[child.start_byte:start] + replace_collapse(grandChild)
                code = code[:start] + replace_collapse(grandChild) + code[end:]
                collapsedChildren.appendleft(collapsedChild)

    code = code[node.start_byte:]
    removedChild = False
    while len(code.strip()) > maxChunkSize and len(collapsedChildren) > 0:
        removedChild = True
        childCode = collapsedChildren.pop()
        try:
            index = code.rindex(childCode)
        except ValueError:
            index = -1
        if index > 0:
            code = code[:index] + code[index + len(childCode):]

    cleanup_code = re.sub(r'^[ \t]+$', '', code.decode('utf-8'), flags=re.MULTILINE)
    cleanup_code = re.sub(r'^[\n]+', '\n', cleanup_code, flags=re.MULTILINE)
    code = cleanup_code.encode('utf-8')

    # if removedChild:
    #     lines = code.splitlines()
    #     firstWhiteSpaceInGroup = -1

    #     for i in range(len(lines) - 1, 0, -1):
    #         if not lines[i].strip():
    #             if firstWhiteSpaceInGroup < 0:
    #                 firstWhiteSpaceInGroup = i
    #         else:
    #             if firstWhiteSpaceInGroup - i > 1:
    #                 lines = [*lines[:i + 1], *lines[firstWhiteSpaceInGroup + 1:]]

    #     code = '\n'.join([x.decode('utf-8') for x in lines])

    return code


def ns_definition_chunk(node: Node, code: bytes, maxChunkSize: int):
    return replace_children(
        node, code, ["declaration_list"],
        ["class_declaration", "struct_declaration"], ["declaration_list"], maxChunkSize
    )


def class_definition_chunk(node: Node, code: bytes, maxChunkSize: int):
    classText = replace_children(
        node, code, ["block", "class_body", "declaration_list"],
        FUNCTION_DECLARATION_NODE_TYPES, FUNCTION_BLOCK_NODE_TYPES, maxChunkSize
    )
    
    isInNamespace = node.parent and \
                    node.parent.type in ['declaration_list'] and \
                    node.parent.parent and \
                    node.parent.parent.type in ['namespace_declaration']
    
    if isInNamespace:
        namespaceNode = node.parent.parent
        namespaceBlock = node.parent
        namespaceHeader = code[namespaceNode.start_byte:namespaceBlock.start_byte]
        indent = " " * node.start_point.column
        combined = f'{namespaceHeader.decode('utf-8')}...\n\n{indent}{classText}'
    
        if len(combined) <= maxChunkSize:
                return combined
            
        if len(classText) <= maxChunkSize:
            return classText

        return classText
    
    return classText


def function_definition_chunk(node: Node, code: bytes, maxChunkSize: int):
    bodyNode = node.children[len(node.children) - 1]
    collapsedBody = replace_collapse(bodyNode)
    signature = code[node.start_byte:bodyNode.start_byte]
    funcText = signature + collapsedBody

    isInClass = node.parent and \
                node.parent.type in ["block", "declaration_list"] and \
                node.parent.parent and \
                node.parent.parent.type in ["class_definition", "class_declaration", "impl_item"]

    if isInClass:
        classNode = node.parent.parent
        classBlock = node.parent
        classHeader = code[classNode.start_byte:classBlock.start_byte]
        indent = " " * node.start_point.column
        combined = f'{classHeader.decode('utf-8')}...\n\n{indent}{funcText.decode('utf-8')}'

        if len(combined) <= maxChunkSize:
            return combined
        
        if len(funcText) <= maxChunkSize:
            return funcText

        firstLine = signature.decode('utf-8').split("\n")[0]
        minimal = f'{firstLine} {collapsedBody.decode('utf-8')}'
        if len(minimal) <= maxChunkSize:
            return minimal

        return collapsedBody

    if len(funcText) <= maxChunkSize:
        return funcText

    firstLine = signature.decode('utf-8').split("\n")[0]
    minimal = f'{firstLine} {collapsedBody.decode('utf-8')}'
    if len(minimal) <= maxChunkSize:
        return minimal

    return collapsedBody


collapsedNodeConstructors = {
    'namespace_declaration': ns_definition_chunk,
    'class_definition': class_definition_chunk,
    'struct_definition': class_definition_chunk,
    'interface_definition': class_definition_chunk,
    'class_declaration': class_definition_chunk,
    'struct_declaration': class_definition_chunk,
    'interface_declaration': class_definition_chunk,
    'impl_item': class_definition_chunk,
    'function_definition': function_definition_chunk,
    'function_declaration': function_definition_chunk,
    'function_item': function_definition_chunk,
    'method_declaration': function_definition_chunk,
    'operator_declaration': function_definition_chunk,
    'constructor_declaration': function_definition_chunk,
}

TEXT_NODE_TYPES = {
    'namespace_declaration': 'namespace',
    'class_declaration': 'class',
    'struct_declaration': 'struct',
    'interface_declaration': 'interface',
    'function_declaration': 'function',
    'method_declaration': 'method',
    'operator_declaration': 'operator',
    'constructor_declaration': 'constructor',
    'compilation_unit': '',
}

def make_text_node(node: Node, content: str, parent: TextNode | None):
    if node.type not in TEXT_NODE_TYPES:
        raise ValueError('unsupported: ' + node.type)
    metadata={
        'start_row': node.start_point.row,
        'end_row': node.end_point.row,
        'name': get_code_path(node),
    }
    if TEXT_NODE_TYPES[node.type]:
        metadata['type'] = TEXT_NODE_TYPES[node.type]
    item = TextNode(
        id_=default_id_func(0, None),
        text=content,
        start_char_idx=node.start_byte,
        end_char_idx=node.end_byte,
        metadata=metadata,
    )
    if parent:
        _add_parent_child_relationship(parent, item)
    return item


def get_code_path(node: Node):
    def _get_name(node: Node):
        name = next((x for x in node.children if x.type in ['identifier', 'qualified_name']), None)
        if name:
            name = name.text.decode('utf-8')
        return name or ''
    
    types = ['interface_declaration', 'struct_declaration',
             'class_declaration', 'method_declaration',
             'constructor_declaration', 'operator_declaration']
    
    if not node:
        return ''
    
    if node.type in ['namespace_declaration', 'file_scoped_namespace_declaration']:
        name = _get_name(node)
        return name or ''
    
    if node.type in types:
        name = _get_name(node)
        parent_node = node.parent
        while parent_node.type not in types + ['namespace_declaration']:
            if (parent_node.type == 'ERROR'):
                parent_node = None
                break
            if parent_node.type == 'compilation_unit':
                parent_node = next((x for x in parent_node.children if x.type in ['file_scoped_namespace_declaration']), None)
                break
            parent_node = parent_node.parent
            if parent_node is None:
                raise ValueError()
        parent = get_code_path(parent_node)
        if parent:
            name = parent + '.' + name
        return name
    
    if node.type == 'compilation_unit':
        # TODO: get types in file
        return ''
    
    raise NotImplementedError()

# def print_tree(tree: Node, level = 0):
#     ident = '  ' * level
#     print(ident, end='')
#     print(tree.type)
#     for child in tree.children:
#         print_tree(child, level+1)

def _add_parent_child_relationship(parent_node: BaseNode, child_node: BaseNode) -> None:
    """Add parent/child relationship between nodes."""
    child_list = parent_node.child_nodes or []
    child_list.append(child_node.as_related_node_info())
    parent_node.relationships[NodeRelationship.CHILD] = child_list

    child_node.relationships[NodeRelationship.PARENT] = (
        parent_node.as_related_node_info()
    )

class SourceCodeNodeParser(NodeParser):
    chunk_size: int = Field(default=512, description='The chunk size')
    
    @classmethod
    def class_name(cls) -> str:
        return "SourceCodeNodeParser"
    
    def get_nodes_from_documents(
        self,
        documents: Sequence[Document],
        show_progress: bool = False,
        **kwargs: Any,
    ) -> List[BaseNode]:
        with self.callback_manager.event(
            CBEventType.NODE_PARSING, payload={EventPayload.DOCUMENTS: documents}
        ) as event:
            all_nodes: List[BaseNode] = []
            documents_with_progress = get_tqdm_iterable(
                documents, show_progress, "Parsing documents into nodes"
            )

            for doc in documents_with_progress:
                nodes_from_doc = self._recursively_get_nodes_from_nodes([doc], 0, show_progress)
                all_nodes.extend(nodes_from_doc)

            event.on_end(payload={EventPayload.NODES: all_nodes})

        return all_nodes
    
    def _recursively_get_nodes_from_nodes(
        self,
        nodes: List[BaseNode],
        level: int,
        show_progress: bool = False,
    ) -> List[BaseNode]:
        nodes_with_progress = get_tqdm_iterable(
            nodes, show_progress, "Parsing documents into nodes"
        )
        sub_nodes = []
        for node in nodes_with_progress:
            file_name = node.metadata['file_name']
            lang = get_lang_for_file(file_name)
            if not lang:
                raise ValueError("Unsupported file type: " + file_name)
            self._default_splitter = SentenceSplitter.from_defaults(chunk_size=self.chunk_size, chunk_overlap=self.chunk_size // 2)
            #self._code_splitter = CodeSplitter.from_defaults(lang, max_chars=self.chunk_size)
            self._code_splitter = self._default_splitter
            # print(f'processing {node.metadata['file_name']}')
            new_nodes = self._code_chunker(file_name, node.text, self.chunk_size)
            for new_node in new_nodes:
                new_node.metadata.update(node.metadata)
                sub_nodes.append(new_node)
        return sub_nodes
    

    def _code_chunker(self, file_name: str, content: str, max_chunk_size: int):
        if not len(content):
            return []

        parser = get_parser_for_file(file_name)
        if parser is None:
            return []

        text_bytes = bytes(content, "utf-8")
        tree = parser.parse(text_bytes)

        return [x for x in self._get_chunks(tree.root_node, text_bytes, max_chunk_size, None)]
    

    def _get_chunks(self, node: Node, code: bytes, max_chunk_size: int, parent: TextNode | None, root=True):
        chunk = self._full_chunk(node, code, max_chunk_size, parent, root)
        if chunk:
            yield from chunk
            return

        item = parent
        if node.type in collapsedNodeConstructors:
            ctor = collapsedNodeConstructors[node.type]
            content = ctor(node, code, max_chunk_size)
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            if len(content) > max_chunk_size:
                try:
                    chunks = self._code_splitter.split_text(content)
                    if len(chunks) <= 2:
                        chunks = [content]
                except ValueError:
                    chunks = self._default_splitter.split_text(content)
                first = True
                for chunk in chunks:
                    tmp = make_text_node(node, chunk, parent)
                    if first:
                        item = tmp
                        first = False
                    yield tmp
            else:
                item = make_text_node(node, content, parent)
                yield item

        for child in node.children:
            yield from self._get_chunks(child, code, max_chunk_size, item, False)


    def _full_chunk(self, node: Node, code: bytes, maxChunkSize: int, parent: TextNode | None, root=True):
        if node.type in FUNCTION_DECLARATION_NODE_TYPES:
            text = node.text.decode('utf-8')
            if len(text) > maxChunkSize:
                try:
                    chunks = self._code_splitter.split_text(text)
                    if len(chunks) <= 2:
                        chunks = [text]
                except ValueError:
                    chunks = self._default_splitter.split_text(text)
                return [make_text_node(node, chunk, parent) for chunk in chunks]
            else:
                return [make_text_node(node, text, parent)]
        elif root or node.type in collapsedNodeConstructors:
            tokenCount = len(node.text)
            if tokenCount < maxChunkSize:
                return [make_text_node(node, node.text.decode('utf-8'), parent)]
        return None
    
    
    def _parse_nodes(
        self, nodes: Sequence[BaseNode], show_progress: bool = False, **kwargs: Any
    ) -> List[BaseNode]:
        return list(nodes)
    

if __name__ == '__main__':
    file_name = r'VBScript.Parser\VBScript.Parser\VBScriptParser.cs'
    with open(file_name, 'rt', encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n')

    doc = Document(text=text, metadata={'file_name': file_name})
    parser = SourceCodeNodeParser(chunk_size=128)
    nodes = parser([doc])
    for node in nodes:
        print('-----------')
        print('Parent:', node.parent_node.node_id if node.parent_node else None)
        print("Name:", node.metadata['name'])
        print("Type:", node.metadata['type'])
        print(node.text)

    # chunks = code_chunker(file_name, text, 500)
    # chunks = [x.relationships for x in chunks]
    # for c in chunks:
    #    print('---')
    #    print(c)