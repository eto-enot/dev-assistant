using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using System.Xml.Linq;
using System.Xml.XPath;

namespace BuildDataset;

class Program
{
    static async Task Main(string[] args)
    {
        if (args.Length < 2) {
            Console.WriteLine("Usage: BuildDataset <repo-path> <xml-doc>");
            return;
        }

        await MakeDataset(args[0], args[1], "dataset.xml");
    }

    /// <summary>
    /// Создание датасета для бенчмарка
    /// </summary>
    /// <param name="directoryPath">Путь к каталогу с кодом</param>
    /// <param name="xmlDoc">Файл xmldoc</param>
    /// <param name="output">Файл, в который записывается датасет</param>
    /// <returns></returns>
    static async Task MakeDataset(string directoryPath, string xmlDoc, string output)
    {
        var info = new Dictionary<string, string>();

        var files = Directory.EnumerateFiles(directoryPath, "*.cs", SearchOption.AllDirectories);
        foreach (string file in files) {
            await ParseFile(file);
            var members = await GetMethods(file);
            foreach (var member in members) {
                info[member] = file;
            }
        }

        int notFound = 0;
        var ds = new XElement("items");
        var doc = XElement.Load(xmlDoc);
        foreach (var member in doc.XPathSelectElements("//member")) {
            string name = (string?)member.Attribute("name") ?? "";
            string type;
            if (name.StartsWith("M:"))
                type = "M";
            else if (name.StartsWith("T:"))
                type = "T";
            else
                continue;

            name = name[2..];
            int braceIdx = name.IndexOf('(');
            if (braceIdx >= 0)
                name = name[..braceIdx];

            if (!info.ContainsKey(name)) {
                ++notFound;
                continue;
            }

            var item = new XElement("item",
                new XElement("file", info[name]),
                new XElement("member", name),   
                new XElement("type", type),
                new XElement("summary", ((string?)member.Element("summary"))?.Trim()));

            ds.Add(item);
        }

        ds.Save(output);
    }

    static readonly string[] _defines = [
        "HAVE_APPCONTEXT",
        "HAVE_ADO_NET",
        "HAVE_APP_DOMAIN",
        "HAVE_ASYNC",
        "HAVE_ASYNC_DISPOSABLE",
        "HAVE_BIG_INTEGER",
        "HAVE_BINARY_FORMATTER",
        "HAVE_BINARY_SERIALIZATION",
        "HAVE_BINARY_EXCEPTION_SERIALIZATION",
        "HAVE_CHAR_TO_LOWER_WITH_CULTURE",
        "HAVE_CHAR_TO_STRING_WITH_CULTURE",
        "HAVE_COM_ATTRIBUTES",
        "HAVE_COMPONENT_MODEL",
        "HAVE_CONCURRENT_COLLECTIONS",
        "HAVE_COVARIANT_GENERICS",
        "HAVE_DATA_CONTRACTS",
        "HAVE_DATE_TIME_OFFSET",
        "HAVE_DB_NULL_TYPE_CODE",
        "HAVE_DYNAMIC",
        "HAVE_EMPTY_TYPES",
        "HAVE_ENTITY_FRAMEWORK",
        "HAVE_EXPRESSIONS",
        "HAVE_FAST_REVERSE",
        "HAVE_FSHARP_TYPES",
        "HAVE_FULL_REFLECTION",
        "HAVE_GUID_TRY_PARSE",
        "HAVE_HASH_SET",
        "HAVE_ICLONEABLE",
        "HAVE_ICONVERTIBLE",
        "HAVE_IGNORE_DATA_MEMBER_ATTRIBUTE",
        "HAVE_INOTIFY_COLLECTION_CHANGED",
        "HAVE_INOTIFY_PROPERTY_CHANGING",
        "HAVE_ISET",
        "HAVE_LINQ",
        "HAVE_MEMORY_BARRIER",
        "HAVE_METHOD_IMPL_ATTRIBUTE",
        "HAVE_NON_SERIALIZED_ATTRIBUTE",
        "HAVE_READ_ONLY_COLLECTIONS",
        "HAVE_REFLECTION_EMIT",
        "HAVE_REGEX_TIMEOUTS",
        "HAVE_SECURITY_SAFE_CRITICAL_ATTRIBUTE",
        "HAVE_SERIALIZATION_BINDER_BIND_TO_NAME",
        "HAVE_STREAM_READER_WRITER_CLOSE",
        "HAVE_STRING_JOIN_WITH_ENUMERABLE",
        "HAVE_TIME_SPAN_PARSE_WITH_CULTURE",
        "HAVE_TIME_SPAN_TO_STRING_WITH_CULTURE",
        "HAVE_TIME_ZONE_INFO",
        "HAVE_TRACE_WRITER",
        "HAVE_TYPE_DESCRIPTOR",
        "HAVE_UNICODE_SURROGATE_DETECTION",
        "HAVE_VARIANT_TYPE_PARAMETERS",
        "HAVE_VERSION_TRY_PARSE",
        "HAVE_XLINQ",
        "HAVE_XML_DOCUMENT",
        "HAVE_XML_DOCUMENT_TYPE",
        "HAVE_CONCURRENT_DICTIONARY",
        "HAVE_INDEXOF_STRING_COMPARISON",
        "HAVE_REPLACE_STRING_COMPARISON",
        "HAVE_REPLACE_STRING_COMPARISON",
        "HAVE_GETHASHCODE_STRING_COMPARISON",
        "HAVE_NULLABLE_ATTRIBUTES",
        "HAVE_DYNAMIC_CODE_COMPILED",
        "HAS_ARRAY_EMPTY",
        "HAVE_DATE_ONLY",
    ];

    /// <summary>
    /// Получение имени типа, соответствующего <paramref name="node"/>
    /// </summary>
    /// <param name="node">Узел, соответствующий типу в AST</param>
    /// <returns>Имя типа</returns>
    static string GetTypeName(SyntaxNode? node)
    {
        var names = new List<string>();

        while (true) {
            if (node is TypeDeclarationSyntax cls) {
                string name = cls.Identifier.Text;
                if (cls.TypeParameterList?.Parameters.Count > 0)
                    name += "`" + cls.TypeParameterList.Parameters.Count;
                names.Add(name);
                node = node.Parent;
            } else if (node is BaseTypeDeclarationSyntax bt) {
                string name = bt.Identifier.Text;
                names.Add(name);
                node = node.Parent;
            } else if (node is BaseNamespaceDeclarationSyntax ns) {
                names.Add(ns.Name.GetText().ToString().Trim());
                break;
            } else
                break;
        }

        names.Reverse();

        return String.Join('.', names);
    }

    /// <summary>
    /// Получение списка имен всех методов (конструкторов, операторов) из файла
    /// </summary>
    /// <param name="filePath">Путь к файлу</param>
    /// <returns>Список имен методов</returns>
    static async Task<List<string>> GetMethods(string filePath)
    {
        string sourceCode = await File.ReadAllTextAsync(filePath);
        var options = CSharpParseOptions.Default.WithPreprocessorSymbols(_defines);
        SyntaxTree syntaxTree = CSharpSyntaxTree.ParseText(sourceCode, options);

        var root = await syntaxTree.GetRootAsync();
        var methods = root.DescendantNodes().OfType<BaseMethodDeclarationSyntax>().ToList();

        var result = new List<string>();
        foreach (var method in methods) {
            string name;
            if (method is MethodDeclarationSyntax m) {
                name = m.Identifier.Text;
                if (m.TypeParameterList?.Parameters.Count > 0)
                    name += "``" + m.TypeParameterList.Parameters.Count;
            } else if (method is ConstructorDeclarationSyntax _) {
                name = "#ctor";
            } else {
                continue;
            }

            string className = GetTypeName(method.Parent);
            result.Add(className);
            result.Add(className + "." + name);
        }

        if (methods.Count == 0) {
            var classes = root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>().ToList();
            foreach (var clazz in classes) {
                result.Add(GetTypeName(clazz));
            }
        }

        return result;
    }

    /// <summary>
    /// Удаление всех xmldoc-комментариев из файла исходного кода
    /// </summary>
    /// <param name="filePath">Путь к файлу</param>
    static async Task ParseFile(string filePath)
    {
        if (!File.Exists(filePath)) {
            throw new FileNotFoundException("File not found.", filePath);
        }

        string sourceCode = await File.ReadAllTextAsync(filePath);
        SyntaxTree syntaxTree = CSharpSyntaxTree.ParseText(sourceCode);

        var root = await syntaxTree.GetRootAsync();

        while (true) {
            var xmlComment = root.DescendantTrivia()
                .FirstOrDefault(t => t.IsKind(SyntaxKind.SingleLineDocumentationCommentTrivia) ||
                           t.IsKind(SyntaxKind.MultiLineDocumentationCommentTrivia));

            if (xmlComment == default)
                break;

            root = root.ReplaceTrivia(xmlComment, SyntaxTriviaList.Empty);
        }

        string modifiedCode = root.ToFullString();

        await File.WriteAllTextAsync(filePath, modifiedCode);
    }
}
