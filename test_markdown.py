from google_docs import markdown_to_docs_requests, create_document
import json
import asyncio

# 9th Grade Algebra Exam in Markdown format
exam_markdown = """# 9th Grade Algebra Exam

**Name:** ____________________  
**Date:** ____________________  
**Class:** ____________________

**Instructions:** This exam has two sections. Complete all problems in both sections. Show all your work to receive full credit. You have 60 minutes to complete this exam.

---

## Section I: Exercises (60 points)

### Linear Equations and Inequalities (20 points)

1. Solve for x: 3x - 7 = 5x + 9 (4 points)

2. Solve the inequality and express your answer in interval notation: 2(x + 3) > 4x - 10 (4 points)

3. A rental car company charges $45 per day plus $0.25 per mile driven. If your total bill was $95 for one day, how many miles did you drive? (6 points)

4. Find the value of x that makes the following equation true: |2x - 3| = 11 (6 points)

### Systems of Equations (20 points)

5. Solve the system of equations by substitution: (6 points)
   * y = 2x + 1
   * 3x - 2y = 4

6. Solve the system of equations by elimination: (6 points)
   * 4x + 3y = 11
   * 2x - 5y = -19

7. The sum of two numbers is 28, and their difference is 4. Find the two numbers. (8 points)

### Polynomials and Factoring (20 points)

8. Multiply: (2x - 5)(x + 3) (4 points)

9. Factor completely: 6x² - x - 2 (6 points)

10. Factor by grouping: xy - 3x + 2y - 6 (4 points)

11. Simplify: (3x²y⁻²)(2xy³)/(6x³y) (6 points)

---

## Section II: Conceptual Questions (40 points)

1. Explain the difference between a function and a relation. Provide an example of each. (8 points)

2. What is the slope-intercept form of a linear equation? Explain what the slope and y-intercept represent in a real-world context. (8 points)

3. A line passes through the points (2, 5) and (4, 9). 
   a) Find the slope of the line. (4 points)
   b) Write the equation of the line in slope-intercept form. (4 points)
   c) What is the y-intercept of this line and what does it represent on a graph? (4 points)

4. Consider the quadratic function f(x) = x² - 6x + 8
   a) Find the vertex of this function. (4 points)
   b) Determine the x-intercepts. (4 points)
   c) Is the vertex a maximum or minimum? Explain why. (4 points)

---

**Bonus Question:** (5 extra points)
Prove algebraically that the sum of consecutive odd integers starting with 1 and ending with 2n-1 equals n².

---

*Good luck!*
"""

async def test_markdown_conversion():
    # Generate the requests for formatting the markdown
    requests = markdown_to_docs_requests(exam_markdown)
    print(requests)
    
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
        'horizontal_rules': False
    }
    
    # Verify specific formatting is applied
    for request in requests:
        if 'updateParagraphStyle' in request:
            style = request['updateParagraphStyle'].get('paragraphStyle', {}).get('namedStyleType', '')
            if 'HEADING' in style:
                elements_check['headings'] = True
        elif 'updateTextStyle' in request:
            style = request['updateTextStyle'].get('textStyle', {})
            if style.get('bold'):
                elements_check['bold'] = True
            if style.get('italic'):
                elements_check['italic'] = True
        elif 'createParagraphBullets' in request:
            elements_check['lists'] = True
    
    # Check for italic "*Good luck!*" text specifically
    italic_good_luck_found = False
    for i, request in enumerate(requests):
        if ('insertText' in request and 
            'Good luck!' in request['insertText'].get('text', '') and
            i+1 < len(requests) and
            'updateTextStyle' in requests[i+1] and
            requests[i+1]['updateTextStyle'].get('textStyle', {}).get('italic')):
            italic_good_luck_found = True
            elements_check['italic'] = True
            print("Found italic formatting for 'Good luck!' text")
            break
    
    # Check for horizontal rule (---) - simplistic check
    for request in requests:
        if 'insertText' in request and '---' in request['insertText'].get('text', ''):
            elements_check['horizontal_rules'] = True
    
    print("\n=== Elements Found ===")
    for element, found in elements_check.items():
        print(f"{element}: {'✅' if found else '❌'}")
    
    # Option to create the document
    create_doc = False  # Set to True to actually create a document
    
    # Debug: Find all insertText requests that contain 'Good luck!'
    print("\n=== Debugging Good luck! text ===")
    for i, request in enumerate(requests):
        if 'insertText' in request and 'Good luck!' in request['insertText'].get('text', ''):
            print(f"Found at index {i}: {request}")
            # Show the next request to see if it applies italic styling
            if i+1 < len(requests):
                print(f"Next request: {requests[i+1]}")
            else:
                print("No next request")
    
    if create_doc:
        try:
            result = await create_document("9th Grade Algebra Exam", exam_markdown)
            print(f"\nCreated document at: {result['url']}")
        except Exception as e:
            print(f"\nError creating document: {str(e)}")
            
    return requests

if __name__ == "__main__":
    # Run the async function with asyncio
    asyncio.run(test_markdown_conversion()) 