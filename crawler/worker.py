from biolib_parser import resolve_page
from crawler.model import PageContent
import time
import random


def generate_beta_random(min_val=1.0, max_val=10.0, target_mean=3.0):
    ratio = (target_mean - min_val) / (max_val - min_val)
    alpha = 2.0  # adjust this to change the steepness of the distribution. Larger, more concentrated.
    beta = alpha * ((1 / ratio) - 1)

    # Generate Beta distribution random numbers between [0, 1]
    x = random.betavariate(alpha, beta)

    # Map to interval [min_val, max_val]
    return min_val + (max_val - min_val) * x

def worker_task(
        page_id: int,
) -> PageContent:
    #################################################
    time.sleep(generate_beta_random(0.2, 9.5, 0.6))
    #################################################

    try:
        return PageContent(
            page_id=page_id,
            content_of_interest=resolve_page(page_id),
            error=None,
        )
    except Exception as e:
        return PageContent(
            page_id=page_id,
            content_of_interest=None,
            error=e,
        )