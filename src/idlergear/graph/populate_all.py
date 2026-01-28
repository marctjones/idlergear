"""Unified script to populate entire knowledge graph."""

from pathlib import Path
from typing import Optional, Dict

from .database import get_database, GraphDatabase
from .schema import initialize_schema
from .populators import (
    GitPopulator,
    CodePopulator,
    TaskPopulator,
    CommitTaskLinker,
    ReferencePopulator,
    WikiPopulator,
    PersonPopulator,
    DependencyPopulator,
    TestPopulator,
    PlanPopulator,
)


def populate_all(
    project_path: Optional[Path] = None,
    max_commits: int = 100,
    code_directory: str = "src",
    wiki_url: Optional[str] = None,
    incremental: bool = True,
    verbose: bool = True,
) -> Dict[str, Dict[str, int]]:
    """Populate entire knowledge graph in one command.

    Runs all populators in the correct order:
    1. Git history (commits, files)
    2. Code symbols (functions, classes)
    3. Tasks (GitHub Issues)
    4. Plans (Plan Objects)
    5. Commit-task linking (parse commit messages)
    6. References (.idlergear/reference/)
    7. Wiki (GitHub wiki)
    8. Person (git authors, contributors)
    9. Dependencies (requirements.txt, package.json, etc.)
    10. Tests (test files and test cases)

    Args:
        project_path: Path to project (defaults to current directory)
        max_commits: Maximum commits to index
        code_directory: Directory to scan for code (default: "src")
        wiki_url: GitHub wiki URL (auto-detected if None)
        incremental: Skip already-indexed data
        verbose: Print progress messages

    Returns:
        Dictionary with results from each populator

    Example:
        >>> from idlergear.graph import populate_all
        >>> results = populate_all(max_commits=100, incremental=True)
        >>> print(f"Indexed {results['git']['commits']} commits")
    """
    project_path = project_path or Path.cwd()
    db = get_database()

    # Initialize schema if needed
    try:
        initialize_schema(db)
        if verbose:
            print("✓ Schema initialized")
    except Exception as e:
        if verbose:
            print(f"Schema already exists or error: {e}")

    results = {}

    # 1. Populate git history
    if verbose:
        print("\n📊 Populating git history...")
    try:
        git_pop = GitPopulator(db, project_path)
        results['git'] = git_pop.populate(
            max_commits=max_commits,
            incremental=incremental
        )
        if verbose:
            print(f"  ✓ {results['git']['commits']} commits indexed")
            print(f"  ✓ {results['git']['files']} files indexed")
            print(f"  ✓ {results['git']['relationships']} relationships created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['git'] = {"error": str(e)}

    # 2. Populate code symbols
    if verbose:
        print("\n📊 Populating code symbols...")
    try:
        code_pop = CodePopulator(db, project_path)
        results['code'] = code_pop.populate_directory(
            code_directory,
            incremental=incremental
        )
        if verbose:
            print(f"  ✓ {results['code']['files']} files scanned")
            print(f"  ✓ {results['code']['symbols']} symbols indexed")
            print(f"  ✓ {results['code']['relationships']} relationships created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['code'] = {"error": str(e)}

    # 3. Populate tasks
    if verbose:
        print("\n📊 Populating tasks...")
    try:
        task_pop = TaskPopulator(db, project_path)
        results['tasks'] = task_pop.populate(
            state="all",
            incremental=incremental
        )
        if verbose:
            print(f"  ✓ {results['tasks']['tasks']} tasks indexed")
            if results['tasks'].get('updated', 0) > 0:
                print(f"  ✓ {results['tasks']['updated']} tasks updated")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['tasks'] = {"error": str(e)}

    # 4. Populate plans
    if verbose:
        print("\n📊 Populating plans...")
    try:
        plan_pop = PlanPopulator(db, project_path)
        results['plans'] = plan_pop.populate(incremental=incremental)
        if verbose:
            print(f"  ✓ {results['plans']['plans']} plans indexed")
            if results['plans'].get('updated', 0) > 0:
                print(f"  ✓ {results['plans']['updated']} plans updated")
            print(f"  ✓ {results['plans']['relationships']} relationships created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['plans'] = {"error": str(e)}

    # 5. Link commits to tasks
    if verbose:
        print("\n📊 Linking commits to tasks...")
    try:
        linker = CommitTaskLinker(db, project_path)
        results['links'] = linker.link_all(incremental=incremental)
        if verbose:
            print(f"  ✓ {results['links']['links_created']} commit-task links created")
            print(f"  ✓ {results['links']['tasks_linked']} tasks linked")
            print(f"  ✓ {results['links']['commits_linked']} commits linked")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['links'] = {"error": str(e)}

    # 5. Populate references
    if verbose:
        print("\n📊 Populating references...")
    try:
        ref_pop = ReferencePopulator(db, project_path)
        results['references'] = ref_pop.populate(incremental=incremental)
        if verbose:
            print(f"  ✓ {results['references']['references']} references indexed")
            if results['references'].get('updated', 0) > 0:
                print(f"  ✓ {results['references']['updated']} references updated")
            print(f"  ✓ {results['references']['relationships']} code links created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['references'] = {"error": str(e)}

    # 6. Populate wiki
    if verbose:
        print("\n📊 Populating wiki documentation...")
    try:
        wiki_pop = WikiPopulator(db, wiki_url=wiki_url)
        results['wiki'] = wiki_pop.populate(incremental=incremental)
        if verbose:
            print(f"  ✓ {results['wiki']['documents']} wiki pages indexed")
            if results['wiki'].get('updated', 0) > 0:
                print(f"  ✓ {results['wiki']['updated']} pages updated")
            print(f"  ✓ {results['wiki']['relationships']} code links created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['wiki'] = {"error": str(e)}

    # 7. Populate persons (contributors)
    if verbose:
        print("\n📊 Populating persons (contributors)...")
    try:
        person_pop = PersonPopulator(db, project_path)
        results['persons'] = person_pop.populate(
            incremental=incremental,
            calculate_ownership=True
        )
        if verbose:
            print(f"  ✓ {results['persons']['persons']} contributors indexed")
            print(f"  ✓ {results['persons']['authored']} commit authorships linked")
            print(f"  ✓ {results['persons']['owns']} file ownerships calculated")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['persons'] = {"error": str(e)}

    # 8. Populate dependencies
    if verbose:
        print("\n📊 Populating dependencies...")
    try:
        dep_pop = DependencyPopulator(db, project_path)
        results['dependencies'] = dep_pop.populate(incremental=incremental)
        if verbose:
            print(f"  ✓ {results['dependencies']['dependencies']} dependencies indexed")
            print(f"  ✓ {results['dependencies']['relationships']} file-dependency links created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['dependencies'] = {"error": str(e)}

    # 9. Populate tests
    if verbose:
        print("\n📊 Populating tests...")
    try:
        test_pop = TestPopulator(db, project_path)
        results['tests'] = test_pop.populate(
            incremental=incremental,
            link_coverage=True
        )
        if verbose:
            print(f"  ✓ {results['tests']['tests']} tests indexed")
            print(f"  ✓ {results['tests']['covers']} coverage links created")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error: {e}")
        results['tests'] = {"error": str(e)}

    # Summary
    if verbose:
        print("\n" + "="*60)
        print("✅ Knowledge graph population complete!")
        print("="*60)

        total_nodes = sum([
            results.get('git', {}).get('commits', 0),
            results.get('git', {}).get('files', 0),
            results.get('code', {}).get('symbols', 0),
            results.get('tasks', {}).get('tasks', 0),
            results.get('plans', {}).get('plans', 0),
            results.get('references', {}).get('references', 0),
            results.get('wiki', {}).get('documents', 0),
            results.get('persons', {}).get('persons', 0),
            results.get('dependencies', {}).get('dependencies', 0),
            results.get('tests', {}).get('tests', 0),
        ])

        total_relationships = sum([
            results.get('git', {}).get('relationships', 0),
            results.get('code', {}).get('relationships', 0),
            results.get('plans', {}).get('relationships', 0),
            results.get('links', {}).get('links_created', 0),
            results.get('references', {}).get('relationships', 0),
            results.get('wiki', {}).get('relationships', 0),
            results.get('persons', {}).get('authored', 0),
            results.get('persons', {}).get('owns', 0),
            results.get('dependencies', {}).get('relationships', 0),
            results.get('tests', {}).get('covers', 0),
        ])

        print(f"\nTotal nodes indexed: ~{total_nodes:,}")
        print(f"Total relationships created: ~{total_relationships:,}")
        print("\n💡 Query the graph with:")
        print("  idlergear_graph_query_task(task_id=N)")
        print("  idlergear_graph_query_file(file_path='...')")
        print("  idlergear_graph_query_symbols(pattern='...')")
        print("="*60)

    return results


def populate_all_quick(project_path: Optional[Path] = None) -> Dict[str, Dict[str, int]]:
    """Quick populate with sensible defaults.

    - 50 most recent commits
    - Incremental mode enabled
    - Less verbose output

    Args:
        project_path: Path to project (defaults to current directory)

    Returns:
        Dictionary with results from each populator
    """
    return populate_all(
        project_path=project_path,
        max_commits=50,
        incremental=True,
        verbose=False,
    )
