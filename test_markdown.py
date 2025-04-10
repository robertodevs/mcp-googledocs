from google_docs import markdown_to_docs_requests, create_document
import json
import asyncio

# 9th Grade Algebra Exam in Markdown format
exam_markdown = """# 9th Grade Mathematics Examination

**Name:** ______________________________  **Date:** ________________

**Class Period:** _______  **Total Points:** 100  **Time:** 60 minutes

## Section A: Algebra (30 points)

1. Solve for x: 3(x - 4) + 2 = 5x - 10
   
2. Factor completely: 2x² + 7x - 15

3. Solve the system of equations:
   ```
   2x + 3y = 12
   4x - y = 5
   ```

4. Write the equation of a line that passes through the points (2, -3) and (4, 1).

5. Simplify the expression: (3x²y³)(4xy⁴)

6. Solve the inequality and graph your solution on a number line: 2x - 5 > 7 or x + 3 ≤ 2


## Section B: Geometry (30 points)

7. Find the area of a triangle with vertices at (0,0), (4,0), and (2,5).

8. In triangle ABC, angle A = 45°, angle B = 60°, and side c = 10 cm. Find angle C.

9. The volume of a cylinder is 200π cm³. If the radius is 5 cm, find the height.

10. A rectangle has a length of 12 cm and a width of 5 cm. Find:
    a) The perimeter
    b) The area
    c) The length of a diagonal

11. Determine whether the triangles with the following side lengths are similar. If they are, state the scale factor.
    Triangle 1: sides of 6, 8, and 10 units
    Triangle 2: sides of 9, 12, and 15 units

12. The measure of an exterior angle of a regular polygon is 24°. How many sides does the polygon have?


## Section C: Statistics and Probability (20 points)

13. The table shows the scores of 30 students on a quiz:
    | Score | 5 | 6 | 7 | 8 | 9 | 10 |
    |-------|---|---|---|---|---|----|
    | Frequency | 3 | 5 | 8 | 7 | 5 | 2 |
    
    Find:
    a) The mean score
    b) The median score
    c) The mode

14. A bag contains 3 red marbles, 5 blue marbles, and 2 green marbles. If two marbles are drawn without replacement, find the probability that:
    a) Both marbles are red
    b) The first marble is blue and the second is green
    c) The marbles are of different colors

15. A spinner has 8 equal sections numbered 1 through 8. Find the probability of spinning:
    a) An even number
    b) A number greater than 6
    c) A prime number


## Section D: Functions and Graphing (20 points)

16. For the function f(x) = 2x² - 3x + 1:
    a) Find f(-2)
    b) Find the value(s) of x where f(x) = 0
    c) Find the vertex of this parabola
    d) Determine whether the parabola opens upward or downward

17. Graph the function g(x) = |x - 3| - 2 and identify:
    a) The y-intercept
    b) The x-intercept(s)
    c) The domain and range

18. Determine whether the relation {(1,3), (2,5), (3,7), (4,9)} represents a function. If it is a function, find an equation that represents it.

19. The function h(x) = 5ˣ models the growth of a certain bacteria population, where x is measured in hours. How many bacteria will there be after 3 hours if there were 10 bacteria initially?

**Bonus Question:** (5 points)
20. Prove that the sum of the angles in any triangle equals 180 degrees.

---

### Formula Sheet:
- Area of triangle = (1/2)bh
- Area of triangle using coordinates = (1/2)|x₁(y₂-y₃) + x₂(y₃-y₁) + x₃(y₁-y₂)|
- Volume of cylinder = πr²h
- Distance formula: d = √[(x₂-x₁)² + (y₂-y₁)²]
- Quadratic formula: x = [-b ± √(b² - 4ac)]/2a
"""

async def test_markdown_conversion():
    # Generate the requests for formatting the markdown
    requests = markdown_to_docs_requests(exam_markdown)
    
    # Count different types of formatting requests
    stats = {
        'insertText': 0,
        'updateTextStyle': 0,
        'updateParagraphStyle': 0,
        'createParagraphBullets': 0,
        'other': 0
    }
    
    for request in requests:
        for key in request:
            if key in stats:
                stats[key] += 1
            else:
                stats['other'] += 1
    
    # Print statistics
    print("=== Markdown Conversion Statistics ===")
    for key, count in stats.items():
        print(f"{key}: {count}")
    
    # Save the first 5 requests for examination
    sample_requests = requests[:5]
    print("\n=== Sample Formatting Requests ===")
    print(json.dumps(sample_requests, indent=2))
    
    # Check for specific elements in the markdown
    elements_check = {
        'headings': False,
        'bold': False,
        'italic': False,
        'lists': False,
        'horizontal_rules': False,
        'code_blocks': False,
        'tables': False
    }
    
    # Detailed formatting examples
    formatting_examples = {
        'bold': [],
        'italic': [],
        'headings': [],
        'lists': [],
        'code_blocks': []
    }
    
    # Verify specific formatting is applied
    for i, request in enumerate(requests):
        if 'updateParagraphStyle' in request:
            style = request['updateParagraphStyle'].get('paragraphStyle', {}).get('namedStyleType', '')
            if 'HEADING' in style:
                elements_check['headings'] = True
                # Store a heading example with its associated text
                text_index = find_text_for_style(requests, i)
                if text_index >= 0:
                    formatting_examples['headings'].append({
                        'style_request': request,
                        'text_request': requests[text_index] if text_index >= 0 else None
                    })
        
        elif 'updateTextStyle' in request:
            style = request['updateTextStyle'].get('textStyle', {})
            
            # Check for bold text
            if style.get('bold'):
                elements_check['bold'] = True
                # Store a bold example with its associated text
                text_index = find_text_for_style(requests, i)
                if text_index >= 0 and len(formatting_examples['bold']) < 3:
                    formatting_examples['bold'].append({
                        'style_request': request,
                        'text_request': requests[text_index] if text_index >= 0 else None
                    })
            
            # Check for italic text
            if style.get('italic'):
                elements_check['italic'] = True
                # Store an italic example with its associated text
                text_index = find_text_for_style(requests, i)
                if text_index >= 0 and len(formatting_examples['italic']) < 3:
                    formatting_examples['italic'].append({
                        'style_request': request,
                        'text_request': requests[text_index] if text_index >= 0 else None
                    })
            
            # Check for code blocks (monospace font)
            if style.get('fontFamily') == 'Consolas':
                elements_check['code_blocks'] = True
                # Store a code block example
                text_index = find_text_for_style(requests, i)
                if text_index >= 0 and len(formatting_examples['code_blocks']) < 1:
                    formatting_examples['code_blocks'].append({
                        'style_request': request,
                        'text_request': requests[text_index] if text_index >= 0 else None
                    })
        
        elif 'createParagraphBullets' in request:
            elements_check['lists'] = True
            # Store a list example
            text_index = find_text_for_style(requests, i)
            if text_index >= 0 and len(formatting_examples['lists']) < 2:
                formatting_examples['lists'].append({
                    'style_request': request,
                    'text_request': requests[text_index] if text_index >= 0 else None
                })
    
    # Check for horizontal rule (---) - simplistic check
    for request in requests:
        if 'insertText' in request and '---' in request['insertText'].get('text', ''):
            elements_check['horizontal_rules'] = True
    
    # Check for tables (simplified approach - look for pipe characters)
    for request in requests:
        if 'insertText' in request and '|' in request['insertText'].get('text', ''):
            elements_check['tables'] = True
    
    print("\n=== Elements Found ===")
    for element, found in elements_check.items():
        print(f"{element}: {'✅' if found else '❌'}")
    
    # Print detailed examples of formatting
    print("\n=== Bold Text Examples ===")
    for i, example in enumerate(formatting_examples['bold']):
        if example['text_request'] and 'insertText' in example['text_request']:
            print(f"Example {i+1}:")
            print(f"Text: {example['text_request']['insertText']['text']}")
            print(f"Style request: {json.dumps(example['style_request'], indent=2)}")
            print()
    
    print("\n=== Italic Text Examples ===")
    for i, example in enumerate(formatting_examples['italic']):
        if example['text_request'] and 'insertText' in example['text_request']:
            print(f"Example {i+1}:")
            print(f"Text: {example['text_request']['insertText']['text']}")
            print(f"Style request: {json.dumps(example['style_request'], indent=2)}")
            print()
    
    print("\n=== Heading Examples ===")
    for i, example in enumerate(formatting_examples['headings']):
        if example['text_request'] and 'insertText' in example['text_request']:
            print(f"Example {i+1}:")
            print(f"Text: {example['text_request']['insertText']['text']}")
            print(f"Style request: {json.dumps(example['style_request'], indent=2)}")
            print()
    
    # Option to create the document
    create_doc = False  # Set to True to actually create a document
    
    if create_doc:
        try:
            result = await create_document("9th Grade Algebra Exam", exam_markdown)
            print(f"\nCreated document at: {result['url']}")
        except Exception as e:
            print(f"\nError creating document: {str(e)}")
            
    return requests

def find_text_for_style(requests, style_index):
    """Find the corresponding insertText request for a style request."""
    if style_index <= 0:
        return -1
    
    style_request = requests[style_index]
    style_range = None
    
    if 'updateTextStyle' in style_request:
        style_range = style_request['updateTextStyle'].get('range')
    elif 'updateParagraphStyle' in style_request:
        style_range = style_request['updateParagraphStyle'].get('range')
    elif 'createParagraphBullets' in style_request:
        style_range = style_request['createParagraphBullets'].get('range')
    
    if not style_range:
        return -1
    
    # Look for text requests with the same or overlapping range
    for i in range(style_index - 1, -1, -1):
        if 'insertText' in requests[i]:
            insert_index = requests[i]['insertText']['location']['index']
            insert_text = requests[i]['insertText']['text']
            
            # Check if this text insertion corresponds to the style
            if insert_index <= style_range['startIndex'] < insert_index + len(insert_text):
                return i
    
    return -1

if __name__ == "__main__":
    # Run the async function with asyncio
    asyncio.run(test_markdown_conversion()) 